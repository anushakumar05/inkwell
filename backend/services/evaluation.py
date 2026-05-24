"""
Evaluation service.

We measure three RAG-specific metrics that have become industry standard
(formalized by the RAGAS paper, Es et al. 2023):

  1. FAITHFULNESS:        Do the claims in the answer follow from the retrieved entries?
                          (Detects hallucination.)
  2. ANSWER RELEVANCE:    Does the answer actually address the question asked?
                          (Detects off-topic responses.)
  3. CONTEXT RELEVANCE:   Were the retrieved entries actually useful for this question?
                          (Detects retrieval quality issues separate from generation.)

Each is scored 0.0 to 1.0 by an LLM judge. We use Claude Sonnet 4.5 as the judge
because it's a different model family from any generator we evaluate, which reduces
self-preference bias (a known issue when a model judges its own output).

Note for the README: LLM-as-judge is NOT a perfect ground truth. It correlates with
human judgment but is imperfect. You should be honest about this in your write-up —
hiring managers respect calibrated honesty more than oversold metrics.
"""
import os
from datetime import datetime
from anthropic import AsyncAnthropic
from pydantic import BaseModel, Field
from beanie import Document

anthropic = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


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
    scores: EvalScores
    is_test_set: bool = False  # True for offline runs, False for live ones
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "eval_runs"


# --- The judge ---

JUDGE_PROMPT = """You are evaluating a RAG (retrieval-augmented generation) system.

You will be given:
- A QUESTION the user asked
- The CONTEXT (journal entries that were retrieved)
- The ANSWER the system produced

Score the answer on three independent dimensions, each 0.0 to 1.0:

1. FAITHFULNESS: How well are the claims in the answer supported by the context?
   1.0 = every claim is supported by the retrieved entries
   0.5 = mix of supported and unsupported claims
   0.0 = the answer hallucinates facts not in the context

2. ANSWER_RELEVANCE: How well does the answer address what was actually asked?
   1.0 = directly answers the question
   0.5 = partial answer or somewhat off-topic
   0.0 = ignores the question

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
    """Score a single RAG response."""
    context_block = "\n\n".join(
        f"[E{i+1}] {hit['preview']}" for i, hit in enumerate(retrieved)
    )

    response = await anthropic.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=512,
        system=JUDGE_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"QUESTION:\n{question}\n\n"
                    f"CONTEXT:\n{context_block}\n\n"
                    f"ANSWER:\n{answer}"
                ),
            }
        ],
        # Force JSON output via the schema
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
):
    """Run evaluation and persist results. Designed to run as a background task."""
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
        scores=scores,
        is_test_set=is_test_set,
    ).insert()
    return scores
