# Inkwell

A journaling app with semantic memory. Write entries in plain text, then search them by *feeling*, ask questions answered from your own past words, and watch your emotional patterns surface over time.

**[Live demo →](https://inkwell-demo.vercel.app)** **·** **[Demo video (2 min) →](https://youtu.be/...)** **·** **[Architecture →](#architecture)**

---

## What it does

- **Semantic search.** Type "when did I feel stuck on a project?" and get back entries that match the *meaning*, not just the words.
- **RAG-powered reflection.** Ask "what have I been struggling with this month?" and the assistant answers using your actual past entries, with inline citations.
- **Mood timeline.** Every entry is automatically scored on valence and energy. A 30-day chart shows the arc of how you've been doing.
- **Pattern detection.** Weekly summaries surface non-obvious patterns ("you write about sleep mostly on Sunday nights").
- **Faithfulness evaluation.** Every RAG response is auto-scored by an LLM judge for faithfulness, answer relevance, and context relevance. A live dashboard tracks the metrics over time.

## The interesting technical challenges

This wasn't a "build a RAG chatbot from a tutorial" project. Three problems made it genuinely hard.

### 1. Personal RAG is noisy RAG

Most RAG tutorials retrieve from clean, factual corpora — Wikipedia, documentation, legal texts. Personal journal entries are the opposite: short, repetitive, full of pronouns ("she said..." — who?), and emotionally loaded. Vanilla cosine search returned semantically-similar-but-actually-irrelevant entries about 30% of the time. Fixes I tried, in order:

| Iteration | Change | Avg faithfulness |
|---|---|---|
| v1 | Plain similarity search, top-5 | 0.72 |
| v2 | Added query rewriting (expand pronouns, add date filters) | 0.81 |
| v3 | Hybrid search (dense + BM25), reranked | 0.87 |
| v4 | Added strict refusal prompt for low-similarity results | 0.91 |

### 2. Mood extraction has to be cheap *and* trustworthy

Mood scoring runs on every entry. At anything above ~$0.001 per entry the unit economics break for a real product. I used `gpt-4o-mini` with strict JSON schema enforcement (Pydantic → JSON Schema → OpenAI structured outputs), which keeps cost at ~$0.0001/entry. The schema enforces a confidence score and the system prompt is explicit about not pathologizing — important when extracting affect data from personal writing.

### 3. Evaluation isn't optional

I'd rather show measured behavior than claim "it works well." Every chat response is scored asynchronously by a different model family (Claude Sonnet 4.5 judging GPT-4o-mini retrieval + Claude generation), reducing self-preference bias. A 30-question curated test set runs offline on every pipeline change. Test set results are checked into `eval_results/` so you can see the progression.

**Honest caveats:** LLM-as-judge is not ground truth. It correlates with human judgment but is imperfect, especially for nuanced "faithfulness" calls. The next step would be a small human-labeled validation set to calibrate the judge.

## Architecture

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐
│   React     │───▶│   FastAPI    │───▶│   MongoDB    │
│  (Vercel)   │    │  (Railway)   │    │  (entries +  │
└─────────────┘    └──────┬───────┘    │   eval runs) │
                          │            └──────────────┘
              ┌───────────┼───────────────┐
              ▼           ▼               ▼
        ┌──────────┐ ┌──────────┐  ┌──────────────┐
        │  OpenAI  │ │  Qdrant  │  │  Anthropic   │
        │ (embed + │ │ (vectors)│  │  (chat +     │
        │   mood)  │ │          │  │   judge)     │
        └──────────┘ └──────────┘  └──────────────┘
```

Async background tasks (FastAPI `BackgroundTasks`) handle embedding, mood extraction, and post-hoc evaluation so the user-facing endpoints stay sub-200ms.

## Stack

**Backend:** FastAPI, Beanie (MongoDB ODM), Qdrant client, OpenAI SDK, Anthropic SDK, LangChain
**Frontend:** React, Vite, TailwindCSS, Recharts, `@uiw/react-md-editor`
**Infra:** Railway (backend + Qdrant), Vercel (frontend), Firebase Auth
**Eval:** Custom LLM-as-judge pipeline, RAGAS for benchmark comparison

## Running locally

```bash
# Backend
cd backend
cp .env.example .env  # fill in OPENAI_API_KEY, ANTHROPIC_API_KEY, MONGO_URL
docker-compose up -d  # starts Qdrant
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend
cd frontend
npm install
npm run dev

# Run the eval suite
cd backend
python -m scripts.run_eval_suite
```

## What I'd do differently

- **Reranker on retrieval.** I used a strict refusal prompt instead of a proper cross-encoder reranker. A reranker would probably be cleaner and faster than relying on the LLM to judge similarity scores it can't see.
- **Human eval calibration.** I should label 50 of my own RAG responses by hand and check how well the LLM judge correlates with my own assessments.
- **Multi-modal entries.** Voice notes would be a natural extension — Whisper transcription into the same pipeline, no other changes needed.

## License

MIT.
