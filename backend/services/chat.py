"""
RAG chat service.

The flow:
  1. Embed the user's question.
  2. Retrieve top-K entries from Qdrant, filtered by user_id.
  3. Format them into a context block with stable citation IDs ([E1], [E2], ...).
  4. Ask Claude to answer using ONLY the context, citing entries by ID.
  5. (For the streaming variant) yield text chunks as they arrive from the model.

Critical design decisions:
- Claude Sonnet for generation: strong instruction-following on grounding/citation
  behavior, which is measured by the eval pipeline.
- Strict system prompt: refusing ("I don't have entries about that") is the CORRECT
  behavior when retrieval comes up empty or off-topic. Hallucination is the failure
  mode we're explicitly designing against.
- Returning the retrieval payload alongside the answer lets the eval pipeline
  score faithfulness without re-running retrieval.
"""
import os
from typing import AsyncIterator
from dotenv import load_dotenv
from anthropic import AsyncAnthropic

load_dotenv()

from services.embeddings import search

anthropic = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

MODEL = "claude-sonnet-4-5"

SYSTEM_PROMPT = """You are a thoughtful assistant helping a user reflect on their own journal entries.

You will be given retrieved journal entries from the user's history, each labeled with an ID like [E1], [E2], etc.

Rules:
1. Answer ONLY using information present in the retrieved entries.
2. When you reference something, cite it inline like [E1] or [E2, E3].
3. If the entries don't contain enough information to answer, say so honestly. Do not speculate or fill in gaps.
4. Be warm but not sycophantic. The user is reflecting on themselves; respect that.
5. Never pathologize or diagnose. You are not their therapist.
6. Quote sparingly — paraphrase in your own words and cite the source.
"""


def format_context(retrieved: list[dict]) -> tuple[str, list[dict]]:
    """Render retrieved entries as a context block + return parallel citation metadata."""
    lines = []
    citations = []
    for i, hit in enumerate(retrieved, start=1):
        cid = f"E{i}"
        date_str = hit["created_at"][:10]
        lines.append(f"[{cid}] (written {date_str}):\n{hit['preview']}")
        citations.append({
            "id": cid,
            "entry_id": hit["entry_id"],
            "created_at": hit["created_at"],
        })
    return "\n\n".join(lines), citations


async def chat(user_id: str, question: str) -> dict:
    """Non-streaming variant — returns the full answer + retrieval metadata.

    Used by the eval pipeline.
    """
    retrieved = await search(user_id=user_id, query=question, limit=5)

    if not retrieved:
        return {
            "answer": "I don't see any entries that relate to that question yet. Try writing more, or asking something different.",
            "citations": [],
            "retrieved": [],
        }

    context, citations = format_context(retrieved)

    response = await anthropic.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Retrieved entries:\n\n{context}\n\n---\n\nUser's question: {question}",
        }],
    )
    answer = response.content[0].text

    return {
        "answer": answer,
        "citations": citations,
        "retrieved": retrieved,
    }


async def chat_stream(user_id: str, question: str) -> AsyncIterator[dict]:
    """Streaming variant for the UI.

    Yields typed events:
      - First yield: {"type": "citations", "data": [...]}  — so the UI can render the
        citation badges before tokens start arriving.
      - Then many yields: {"type": "text", "data": "..."} — token chunks.
      - On empty retrieval: a single text yield with a refusal message, no citations.
    """
    retrieved = await search(user_id=user_id, query=question, limit=5)

    if not retrieved:
        yield {"type": "citations", "data": []}
        yield {"type": "text", "data": "I don't see any entries that relate to that question yet."}
        return

    context, _ = format_context(retrieved)
    citations = [
        {"id": f"E{i+1}", "entry_id": hit["entry_id"], "created_at": hit["created_at"]}
        for i, hit in enumerate(retrieved)
    ]

    # Send citations first so the UI can render badges before the answer streams.
    yield {"type": "citations", "data": citations}

    async with anthropic.messages.stream(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Retrieved entries:\n\n{context}\n\n---\n\nUser's question: {question}",
        }],
    ) as stream:
        async for text in stream.text_stream:
            yield {"type": "text", "data": text}