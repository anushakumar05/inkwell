"""
Offline evaluation runner.

Run after any change to:
  - The chat system prompt
  - The retrieval pipeline (chunk size, embeddings model, hybrid search, etc.)
  - The generation model

Usage:
    python -m scripts.run_eval_suite

Output:
    - Console: summary table + per-question scores
    - File:    backend/eval_results/{ISO timestamp}.json
                Commit these to track scores over time.
"""
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from statistics import mean

from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from dotenv import load_dotenv
import os

load_dotenv()

from models.entry import Entry
from services.chat import chat
from services.evaluation import EvalRun, score_and_store
from scripts.eval_test_set import TEST_SET


# The eval suite runs against a specific user's corpus. We pick the same user
# every time so scores are comparable across runs.
def get_test_user_id() -> str:
    uid = os.environ.get("EVAL_USER_ID")
    if not uid:
        print("ERROR: set EVAL_USER_ID env var to your Firebase UID before running.")
        print("  export EVAL_USER_ID=your-uid-here")
        sys.exit(1)
    return uid


async def run_one(user_id: str, item: dict) -> dict:
    """Run a single question end-to-end and return its scores."""
    question = item["question"]
    chat_result = await chat(user_id=user_id, question=question)

    scores = await score_and_store(
        user_id=user_id,
        question=question,
        chat_result=chat_result,
        is_test_set=True,
    )

    if scores is None:
        return {
            "id": item["id"],
            "category": item["category"],
            "question": question,
            "answer": chat_result["answer"][:200],
            "num_retrieved": len(chat_result["retrieved"]),
            "error": "evaluation failed",
        }

    return {
        "id": item["id"],
        "category": item["category"],
        "question": question,
        "answer": chat_result["answer"][:200],
        "num_retrieved": len(chat_result["retrieved"]),
        "faithfulness": scores.faithfulness,
        "answer_relevance": scores.answer_relevance,
        "context_relevance": scores.context_relevance,
        "notes": scores.notes,
    }


async def main():
    user_id = get_test_user_id()

    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    await init_beanie(
        database=client[os.environ["DB_NAME"]],
        document_models=[Entry, EvalRun],
    )

    cases = [c for c in TEST_SET if not c.get("skip")]
    print(f"Running eval suite — {len(cases)} test cases\n")

    # Run cases in parallel for speed (eval calls are I/O-bound).
    # Limit concurrency to avoid Anthropic rate limits.
    sem = asyncio.Semaphore(3)
    async def bounded(item):
        async with sem:
            result = await run_one(user_id, item)
            mark = "✓" if "faithfulness" in result else "✗"
            f = result.get("faithfulness")
            print(f"  {mark} {item['id']}  f={f:.2f}" if f is not None else f"  {mark} {item['id']}  (failed)")
            return result

    results = await asyncio.gather(*(bounded(c) for c in cases))

    # Aggregate
    successful = [r for r in results if "faithfulness" in r]
    summary = {
        "timestamp": datetime.utcnow().isoformat(),
        "n_questions": len(cases),
        "n_successful": len(successful),
        "avg_faithfulness": mean([r["faithfulness"] for r in successful]) if successful else 0,
        "avg_answer_relevance": mean([r["answer_relevance"] for r in successful]) if successful else 0,
        "avg_context_relevance": mean([r["context_relevance"] for r in successful]) if successful else 0,
        "results": results,
    }

    # Print summary
    print(f"\n{'='*60}")
    print(f"  {len(successful)}/{len(cases)} cases scored successfully")
    print(f"  Faithfulness:      {summary['avg_faithfulness']:.3f}")
    print(f"  Answer relevance:  {summary['avg_answer_relevance']:.3f}")
    print(f"  Context relevance: {summary['avg_context_relevance']:.3f}")
    print(f"{'='*60}\n")

    # Per-category breakdown — useful for spotting weak areas
    by_cat = {}
    for r in successful:
        by_cat.setdefault(r["category"], []).append(r["faithfulness"])
    print("By category (faithfulness):")
    for cat, vals in sorted(by_cat.items()):
        print(f"  {cat:20s} {mean(vals):.3f}  (n={len(vals)})")

    # Save to disk
    out_dir = Path("eval_results")
    out_dir.mkdir(exist_ok=True)
    fname = out_dir / f"{summary['timestamp'].replace(':', '-')}.json"
    fname.write_text(json.dumps(summary, indent=2))
    print(f"\nFull report: {fname}")


if __name__ == "__main__":
    asyncio.run(main())