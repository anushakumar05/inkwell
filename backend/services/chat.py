"""
RAG chat service.

The flow:
  1. Embed the user's question.
  2. Retrieve top-K entries from Qdrant, filtered by user_id.
  3. Format them into a context block with stable citation IDs.
  4. Ask the LLM to answer using ONLY the context, and to cite entries by ID.
  5. Stream the response back to the client.

Critical design decisions:
- We use Claude Sonnet 4.5 here. It's the strongest at instruction-following for
  grounding/citation behavior, which is what we'll be evaluating.
- The system prompt is explicit about when to refuse. Saying "I don't have entries
  about that" is the CORRECT behavior; hallucinating is the failure mode we're
  measuring against in Phase 5.
- We return both the answer and the retrieved context, so the eval pipeline (Phase 5)
  can score faithfulness without re-running retrieval.
"""
import os
from typing import AsyncIterator
from anthropic import AsyncAnthropic
from services.embeddings import search

anthropic = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

SYSTEM_PROMPT = """You are a thoughtful assistant helping a user reflect on their own journal entries.

You will be given a set of retrieved journal entries from the user's history, each labeled with an ID like [E1], [E2], etc.

Rules:
1. Answer ONLY using information present in the retrieved entries.
2. When you reference something, cite it inline like [E1] or [E2, E3].
3. If the entries don't contain enough information to answer, say so honestly. Do not speculate.
4. Be warm but not sycophantic. The user is reflecting on themselves; respect that.
5. Never pathologize or diagnose. You are not their therapist.
6. Quote sparingly — paraphrase the entries in your own words and cite them.
"""


def format_context(retrieved: list[dict]) -> tuple[str, list[dict]]:
    """Render entries as a context block + return a parallel list for citation lookup."""
    lines = []
    citations = []
    for i, hit in enumerate(retrieved, start=1):
        cid = f"E{i}"
        lines.append(f"[{cid}] (written {hit['created_at']}):\n{hit['preview']}")
        citations.append({"id": cid, "entry_id": hit["entry_id"], "created_at": hit["created_at"]})
    return "\n\n".join(lines), citations


async def chat(user_id: str, question: str) -> dict:
    """Non-streaming variant — returns full answer + retrieval metadata.

    Used by the eval pipeline. The user-facing endpoint streams (see api/chat.py).
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
        model="claude-sonnet-4-5",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Retrieved entries:\n\n{context}\n\n---\n\nUser's question: {question}",
            }
        ],
    )
    answer = response.content[0].text

    return {
        "answer": answer,
        "citations": citations,
        "retrieved": retrieved,  # full retrieval payload for eval
    }


async def chat_stream(user_id: str, question: str) -> AsyncIterator[str]:
    """Streaming variant for the UI."""
    retrieved = await search(user_id=user_id, query=question, limit=5)
    if not retrieved:
        yield "I don't see any entries that relate to that question yet."
        return

    context, _ = format_context(retrieved)

    async with anthropic.messages.stream(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Retrieved entries:\n\n{context}\n\n---\n\nUser's question: {question}",
            }
        ],
    ) as stream:
        async for text in stream.text_stream:
            yield text
