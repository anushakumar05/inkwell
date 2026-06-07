"""
Chat endpoints — RAG-powered Q&A over the user's own journal entries.
"""
import asyncio
import json
from typing import AsyncIterator
from fastapi import APIRouter, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from auth.firebase import require_user
from services.chat import chat, chat_stream
from services.embeddings import search
from services.evaluation import score_and_store

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    answer: str
    citations: list[dict]


@router.post("", response_model=ChatResponse)
async def chat_endpoint(
    payload: ChatRequest,
    background: BackgroundTasks,
    user_id: str = Depends(require_user),
):
    """Non-streaming chat. Returns the full answer; evaluation runs in the background."""
    result = await chat(user_id=user_id, question=payload.question)
    background.add_task(
        score_and_store,
        user_id=user_id,
        question=payload.question,
        chat_result=result,
        is_test_set=False,
    )
    return ChatResponse(answer=result["answer"], citations=result["citations"])


@router.post("/stream")
async def chat_stream_endpoint(
    payload: ChatRequest,
    user_id: str = Depends(require_user),
):
    """Streaming chat with background evaluation."""
    captured = {"answer": "", "retrieved": []}

    async def run_eval_after():
        """Detached task that runs after the stream completes. Truly fire-and-forget:
        survives the client closing the SSE connection."""
        if captured["answer"] and captured["retrieved"]:
            print(f"🔬 Starting eval for: {payload.question[:60]}...")
            result = await score_and_store(
                user_id=user_id,
                question=payload.question,
                chat_result={
                    "answer": captured["answer"],
                    "retrieved": captured["retrieved"],
                },
                is_test_set=False,
            )
            if result:
                print(f"✓ Eval stored: f={result.faithfulness:.2f} a={result.answer_relevance:.2f} c={result.context_relevance:.2f}")
            else:
                print("⚠️  Eval returned None (check earlier ⚠️ for the actual error)")

    async def event_generator() -> AsyncIterator[str]:
        retrieved = await search(user_id=user_id, query=payload.question, limit=5)
        captured["retrieved"] = retrieved

        async for chunk in chat_stream(user_id=user_id, question=payload.question):
            if chunk["type"] == "text":
                captured["answer"] += chunk["data"]
            yield f"data: {json.dumps(chunk)}\n\n"
        yield "data: {\"type\": \"done\"}\n\n"

        # Schedule the eval as a DETACHED task. It runs independently of this
        # generator's lifecycle, so it survives the client closing the connection.
        asyncio.create_task(run_eval_after())

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )