"""
Entry CRUD endpoints.

Note: this version has NO auth yet. We'll bolt that on tomorrow. For now,
every endpoint accepts a `user_id` query param so we can test multi-user behavior
manually via the /docs page.
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from beanie import PydanticObjectId
from services import embeddings

from models.entry import Entry
from auth.firebase import require_user

router = APIRouter(prefix="/entries", tags=["entries"])


# --- Request/Response schemas ---
# These are SEPARATE from the database model. Good practice: the API shape
# should not be tightly coupled to the DB shape. It lets you evolve them
# independently.

class EntryCreate(BaseModel):
    content: str = Field(min_length=1, max_length=50_000)


class EntryUpdate(BaseModel):
    content: str = Field(min_length=1, max_length=50_000)


class EntryResponse(BaseModel):
    id: str
    content: str
    word_count: int
    created_at: datetime
    updated_at: datetime
    # Mood is None until the background worker processes it (Week 3)
    mood: Optional[dict] = None

    @classmethod
    def from_doc(cls, entry: Entry) -> "EntryResponse":
        return cls(
            id=str(entry.id),
            content=entry.content,
            word_count=entry.word_count,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
            mood=entry.mood.model_dump() if entry.mood else None,
        )

class SearchResult(BaseModel):
    entry_id: str
    preview: str
    created_at: str
    score: float

# --- Endpoints ---

@router.post("", response_model=EntryResponse, status_code=201)
async def create_entry(
    payload: EntryCreate,
    background: BackgroundTasks,
    user_id: str = Depends(require_user),
):
    entry = Entry(
        user_id=user_id,
        content=payload.content,
        word_count=len(payload.content.split()),
    )
    await entry.insert()

    # Embed + index in the background so the user gets an instant response.
    background.add_task(
        embeddings.index_entry,
        entry_id=str(entry.id),
        user_id=user_id,
        content=entry.content,
        created_at_iso=entry.created_at.isoformat(),
    )
    return EntryResponse.from_doc(entry)


@router.get("", response_model=list[EntryResponse])
async def list_entries(
    user_id: str = Depends(require_user),
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
):
    entries = (
        await Entry.find(Entry.user_id == user_id)
        .sort(-Entry.created_at)  # newest first
        .skip(skip)
        .limit(limit)
        .to_list()
    )
    return [EntryResponse.from_doc(e) for e in entries]


@router.get("/{entry_id}", response_model=EntryResponse)
async def get_entry(entry_id: PydanticObjectId, user_id: str = Depends(require_user)):
    entry = await Entry.get(entry_id)
    if not entry or entry.user_id != user_id:
        raise HTTPException(404, "Entry not found")
    return EntryResponse.from_doc(entry)


@router.patch("/{entry_id}", response_model=EntryResponse)
async def update_entry(
    entry_id: PydanticObjectId,
    payload: EntryUpdate,
    background: BackgroundTasks,
    user_id: str = Depends(require_user),
):
    entry = await Entry.get(entry_id)
    if not entry or entry.user_id != user_id:
        raise HTTPException(404, "Entry not found")

    entry.content = payload.content
    entry.word_count = len(payload.content.split())
    entry.updated_at = datetime.utcnow()
    await entry.save()

    # Re-embed since the content changed. Because to_point_id is deterministic,
    # this overwrites the existing vector rather than creating a duplicate.
    background.add_task(
        embeddings.index_entry,
        entry_id=str(entry.id),
        user_id=user_id,
        content=entry.content,
        created_at_iso=entry.created_at.isoformat(),
    )
    return EntryResponse.from_doc(entry)


@router.delete("/{entry_id}", status_code=204)
async def delete_entry(
    entry_id: PydanticObjectId,
    background: BackgroundTasks,
    user_id: str = Depends(require_user),
):
    entry = await Entry.get(entry_id)
    if not entry or entry.user_id != user_id:
        raise HTTPException(404, "Entry not found")
    await entry.delete()
    background.add_task(embeddings.delete_entry, entry_id=str(entry_id))

@router.get("/search/semantic", response_model=list[SearchResult])
async def semantic_search(
    q: str = Query(..., min_length=1, description="Natural language search query"),
    limit: int = Query(5, ge=1, le=20),
    user_id: str = Depends(require_user),
):
    results = await embeddings.search(user_id=user_id, query=q, limit=limit)
    return results