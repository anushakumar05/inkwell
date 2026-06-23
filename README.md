# Inkwell

A journaling app with semantic memory. Write entries in plain text, then search them by *feeling*, ask questions answered from your own past words, and watch your emotional patterns surface over time.

**[Live demo](https://inkwell-ak.vercel.app)** · **[Demo video (90s)](link)**

---

## What it does

- **RAG-powered reflection.** Interact with a context-aware chatbot where you can ask questions and receive answers grounded on your actual past entries - no hallucinations.
- **Semantic search.** Quickly search through past entries by typing a keyword (e.g. "overwhelmed") to read back on when you felt a certain way - not just keyword-based matching.
- **Mood timeline.** Every entry is automatically scored on its valence and energy. A visual representation of how you've been doing over the past 90 days helps you analyze your emotional trends.
- **Recurring themes.** Visually see what you most write about.
- **Frequency heatmap.** GitHub-style calendar showing when entries get written to encourage daily/regular journaling.
- **Faithfulness evaluation.** Every RAG response is auto-scored by an LLM judge on faithfulness, answer relevance, and context relevance. There is also a 25-question offline test suite that prevents the chat pipeline from regressing.

## What makes Inkwell Special

### 1. Reduces Chances of LLM Hallucinations

When retrieval returns weak matches or comes up empty, the system says "I don't see any entries about that" instead of fabricating. The eval framework caught this — test cases designed to expect refusal had brutal faithfulness scores until the prompt was tightened.

### 2. Mood extraction has to be cheap *and* trustworthy

Mood scoring runs on every entry. At anything above ~$0.001 per entry the unit economics break for a real product. I used `gpt-4o-mini` with strict structured outputs (Pydantic schema → OpenAI's `parse` helper) at ~$0.0001/entry. The two-axis valence/energy scoring is grounded in psychology research, not invented. The system prompt is deliberately written to not pathologize normal emotions or project feelings the user didn't express — an important guardrail when extracting affect from personal writing.

### 3. Evaluation isn't optional

Most RAG demos ship without measuring quality. This one doesn't. Three RAGAS-paper metrics (Es et al. 2023):

| Metric | What it catches |
|---|---|
| **Faithfulness** | Hallucination — claims not supported by retrieved entries |
| **Answer relevance** | Off-topic or evasive answers |
| **Context relevance** | Retrieval quality, isolated from generation quality |

Every chat response is auto-scored asynchronously via a detached `asyncio.create_task` so the eval survives the user closing the SSE connection. A 25-question offline test set in `backend/scripts/eval_test_set.py` covers synthesis, specific lookup, comparison, refusal-expected, and edge cases. Run `python -m scripts.run_eval_suite` to execute the whole thing; timestamped result files in `backend/eval_results/` are checked into git so score progression over time is visible.

LLM-as-judge correlates with human judgment but is imperfect. Calibrating against a small human-labeled set would be the next step a production team would take.

## Architecture
