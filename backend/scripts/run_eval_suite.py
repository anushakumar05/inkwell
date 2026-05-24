"""
Offline test set runner.

Run this from the command line whenever you make a change to the RAG pipeline
(new model, new prompt, new chunking, etc.). It executes a fixed set of questions
against a fixed set of seed entries and reports aggregate metrics.

Usage:
    python -m scripts.run_eval_suite

Output:
    - Console: summary table with averages and per-question scores
    - File:    eval_results/{timestamp}.json with full results

THIS IS THE FILE THAT GETS YOU HIRED. Show this in the README. Show the metrics
over time as you iterate. "v1: 72% faithfulness. v3 (added query rewriting): 87%"
is exactly the kind of bullet that makes an interviewer lean forward.
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path
from statistics import mean

from services.chat import chat
from services.evaluation import evaluate_response

# A test set is a list of (question, ideal_behavior) pairs.
# The ideal_behavior isn't used by the judge directly — it's for YOU to read
# when you're debugging why a question scored low.
TEST_SET = [
    {
        "question": "What have I been struggling with lately?",
        "ideal_behavior": "Should synthesize themes across recent negative-valence entries.",
    },
    {
        "question": "When was the last time I felt really happy?",
        "ideal_behavior": "Should find a positive-valence entry and reference its date.",
    },
    {
        "question": "Do I write more about work or relationships?",
        "ideal_behavior": "Should compare theme frequencies. If insufficient data, say so.",
    },
    {
        "question": "What's the meaning of life?",
        "ideal_behavior": "Should refuse — this isn't grounded in journal entries. Tests guardrails.",
    },
    {
        "question": "Did I mention my friend Maya recently?",
        "ideal_behavior": "Tests proper-noun retrieval. Should find entries mentioning Maya, or honestly say no.",
    },
    # ... add 15+ more, covering: positive questions, retrieval-edge-case questions,
    # questions you EXPECT to fail (the refusal cases), questions about specific dates,
    # questions about themes.
]

TEST_USER_ID = "eval_seed_user"  # A user pre-populated with seed entries


async def run_one(item: dict) -> dict:
    question = item["question"]
    chat_result = await chat(user_id=TEST_USER_ID, question=question)
    scores = await evaluate_response(
        question=question,
        answer=chat_result["answer"],
        retrieved=chat_result["retrieved"],
    )
    return {
        "question": question,
        "ideal_behavior": item["ideal_behavior"],
        "answer": chat_result["answer"],
        "scores": scores.model_dump(),
        "num_retrieved": len(chat_result["retrieved"]),
    }


async def main():
    print(f"Running eval suite with {len(TEST_SET)} questions...")
    results = await asyncio.gather(*(run_one(item) for item in TEST_SET))

    faithfulness_scores = [r["scores"]["faithfulness"] for r in results]
    relevance_scores = [r["scores"]["answer_relevance"] for r in results]
    context_scores = [r["scores"]["context_relevance"] for r in results]

    summary = {
        "timestamp": datetime.utcnow().isoformat(),
        "n_questions": len(TEST_SET),
        "avg_faithfulness": mean(faithfulness_scores),
        "avg_answer_relevance": mean(relevance_scores),
        "avg_context_relevance": mean(context_scores),
        "results": results,
    }

    print(f"\n{'='*60}")
    print(f"Faithfulness:      {summary['avg_faithfulness']:.3f}")
    print(f"Answer relevance:  {summary['avg_answer_relevance']:.3f}")
    print(f"Context relevance: {summary['avg_context_relevance']:.3f}")
    print(f"{'='*60}\n")

    out_dir = Path("eval_results")
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / f"{summary['timestamp']}.json"
    out_file.write_text(json.dumps(summary, indent=2))
    print(f"Wrote {out_file}")


if __name__ == "__main__":
    asyncio.run(main())
