"""
Entry model — represents a single journal entry.
Mood fields are populated asynchronously after creation by the mood extraction worker.
"""
from datetime import datetime
from typing import Optional
from beanie import Document, Indexed
from pydantic import BaseModel, Field


class MoodAnalysis(BaseModel):
    """Structured output from the LLM mood extractor.

    Valence: -1 (negative) to +1 (positive)
    Energy:   -1 (low/calm) to +1 (high/agitated)
    These two axes come from circumplex theory of affect — standard in psych research.
    """
    valence: float = Field(ge=-1.0, le=1.0)
    energy: float = Field(ge=-1.0, le=1.0)
    dominant_emotion: str  # e.g. "anxious", "content", "grateful"
    themes: list[str]      # e.g. ["work stress", "family", "self-doubt"]
    confidence: float = Field(ge=0.0, le=1.0)


class Entry(Document):
    user_id: Indexed(str)            # Firebase UID
    content: str                      # raw markdown
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    word_count: int

    # Populated by background workers — nullable until processed
    mood: Optional[MoodAnalysis] = None
    embedding_status: str = "pending"  # pending | indexed | failed

    class Settings:
        name = "entries"
        indexes = [
            [("user_id", 1), ("created_at", -1)],  # for fast user timeline queries
        ]
