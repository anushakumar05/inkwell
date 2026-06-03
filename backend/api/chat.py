"""
Chat endpoints — RAG-powered Q&A over the user's own journal entries.

Two endpoints:
  POST /chat           — non-streaming, returns the full answer at once.
                         Used by the Week 5 eval pipeline.
  POST /chat/stream    — Server-Sent Events stream of citations + text chunks.
                         Used by the UI for snappy, real-time feedback.
"""
import json
from typing import AsyncIterator
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from auth.firebase import require_user
from services.chat import chat, chat_stream

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    answer: str
    citations: list[dict]


@router.post("", response_model=ChatResponse)
async def chat_endpoint(payload: ChatRequest, user_id: str = Depends(require_user)):
    """Non-streaming chat. Returns the full answer once generation completes."""
    result = await chat(user_id=user_id, question=payload.question)
    return ChatResponse(answer=result["answer"], citations=result["citations"])


@router.post("/stream")
async def chat_stream_endpoint(payload: ChatRequest, user_id: str = Depends(require_user)):
    """Streaming chat via Server-Sent Events.

    Each event has the form `data: <json>\\n\\n` where the JSON has a `type`
    ("citations" or "text") and a `data` payload. The client parses each event
    as it arrives and updates the UI incrementally.
    """
    async def event_generator() -> AsyncIterator[str]:
        async for chunk in chat_stream(user_id=user_id, question=payload.question):
            # SSE format: `data: <line>\n\n`. JSON-encode the chunk so newlines
            # inside the payload don't break the protocol.
            yield f"data: {json.dumps(chunk)}\n\n"
        # Signal end of stream so the client can close cleanly.
        yield "data: {\"type\": \"done\"}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disables proxy buffering if you deploy behind nginx
        },
    )