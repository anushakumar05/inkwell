"""
Evaluation service — LLM-as-judge for RAG quality.

We measure three RAG-specific metrics formalized by the RAGAS paper (Es et al. 2023):

  1. FAITHFULNESS:        Do claims in the answer follow from the retrieved entries?
                          Detects hallucination.
  2. ANSWER_RELEVANCE:    Does the answer address the question that was asked?
                          Detects off-topic or evasive responses.
  3. CONTEXT_RELEVANCE:   Were the retrieved entries actually useful for this question?
                          Isolates retrieval quality from generation quality.

Each is scored 0.0–1.0 by Claude Sonnet acting as judge. We're honest in the README
that LLM-as-judge correlates with human judgment but is imperfect — a real production
team would calibrate the judge against a small human-labeled set.
"""
import os
from datetime import datetime
from anthropic import AsyncAnthropic
from pydantic import BaseModel, Field
from beanie import Document
from dotenv import load_dotenv

load_dotenv()

anthropic = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
JUDGE_MODEL = "claude-sonnet-4-5"


# --- Schema for the judge's output ---

class EvalScores(BaseModel):
    faithfulness: float = Field(ge=0.0, le=1.0)
    answer_relevance: float = Field(ge=0.0, le=1.0)
    context_relevance: float = Field(ge=0.0, le=1.0)
    notes: str  # the judge's reasoning — invaluable for debugging


# --- MongoDB document for persisting eval runs ---

class EvalRun(Document):
    user_id: str
    question: str
    answer: str
    retrieved_previews: list[str]
    num_retrieved: int
    faithfulness: float
    answer_relevance: float
    context_relevance: float
    notes: str
    is_test_set: bool = False  # True for offline runs, False for live ones
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "eval_runs"
        indexes = [
            [("user_id", 1), ("created_at", -1)],
            [("is_test_set", 1)],
        ]


# --- The judge ---

JUDGE_PROMPT = """You are evaluating a RAG (retrieval-augmented generation) system that answers questions from a user's personal journal entries.

You will be given:
- A QUESTION the user asked
- The CONTEXT (journal entries that were retrieved)
- The ANSWER the system produced

Score the answer on three independent dimensions, each 0.0 to 1.0:

1. FAITHFULNESS: How well are the claims in the answer supported by the context?
   1.0 = every claim is supported by the retrieved entries
   0.5 = mix of supported and unsupported claims
   0.0 = the answer hallucinates facts not in the context
   A correct REFUSAL ("I don't have entries about that") scores 1.0 here.

2. ANSWER_RELEVANCE: How well does the answer address what was actually asked?
   1.0 = directly answers the question
   0.5 = partial answer or somewhat off-topic
   0.0 = ignores the question
   A correct REFUSAL when retrieval was empty also scores 1.0 here.

3. CONTEXT_RELEVANCE: How useful were the retrieved entries for this specific question?
   1.0 = retrieved entries are clearly relevant
   0.5 = some relevant, some noise
   0.0 = retrieved entries are unrelated to the question

Also provide a short "notes" string (1-2 sentences) explaining your scoring,
especially any concerns. Be strict — this is for quality monitoring.
"""


async def evaluate_response(
    question: str,
    answer: str,
    retrieved: list[dict],
) -> EvalScores:
    """Score a single RAG response. Returns validated EvalScores or raises."""
    if retrieved:
        context_block = "\n\n".join(
            f"[E{i+1}] (written {hit['created_at'][:10]}):\n{hit['preview']}"
            for i, hit in enumerate(retrieved)
        )
    else:
        context_block = "(no entries were retrieved)"

    response = await anthropic.messages.create(
        model=JUDGE_MODEL,
        max_tokens=512,
        system=JUDGE_PROMPT,
        messages=[{
            "role": "user",
            "content": (
                f"QUESTION:\n{question}\n\n"
                f"CONTEXT:\n{context_block}\n\n"
                f"ANSWER:\n{answer}"
            ),
        }],
        # Force structured output via tool use — guarantees we get valid scores back.
        tools=[{
            "name": "submit_evaluation",
            "description": "Submit the three eval scores plus notes.",
            "input_schema": EvalScores.model_json_schema(),
        }],
        tool_choice={"type": "tool", "name": "submit_evaluation"},
    )

    tool_use = next(b for b in response.content if b.type == "tool_use")
    return EvalScores.model_validate(tool_use.input)


async def score_and_store(
    user_id: str,
    question: str,
    chat_result: dict,
    is_test_set: bool = False,
) -> EvalScores | None:
    """Run evaluation and persist results. Designed to run as a background task.

    Returns None on failure so the caller's background loop doesn't blow up.
    """
    try:
        scores = await evaluate_response(
            question=question,
            answer=chat_result["answer"],
            retrieved=chat_result["retrieved"],
        )
        await EvalRun(
            user_id=user_id,
            question=question,
            answer=chat_result["answer"],
            retrieved_previews=[r["preview"] for r in chat_result["retrieved"]],
            num_retrieved=len(chat_result["retrieved"]),
            faithfulness=scores.faithfulness,
            answer_relevance=scores.answer_relevance,
            context_relevance=scores.context_relevance,
            notes=scores.notes,
            is_test_set=is_test_set,
        ).insert()
        return scores
    except Exception as e:
        print(f"⚠️  Evaluation failed: {e}")
        return None