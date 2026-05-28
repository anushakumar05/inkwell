"""
Embedding service.

Why these design choices:
- text-embedding-3-small: 1536 dim, cheap, strong on semantic similarity for short text.
- Qdrant over Pinecone/Weaviate: free self-hostable, has metadata filtering we need
  for multi-tenancy (filter by user_id at query time, never cross-leak entries between users).
- Cosine distance: standard for semantic similarity with normalized embeddings.
"""
import os
import uuid
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536
COLLECTION = "journal_entries"

# Qdrant point IDs must be an int or a UUID. MongoDB ObjectIds are neither, so we
# deterministically derive a UUID from the entry's string id. "Deterministic" means
# the same entry_id always produces the same UUID — so updates overwrite the right
# point and deletes remove the right one, instead of creating duplicates.
_QDRANT_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # any fixed UUID


def to_point_id(entry_id: str) -> str:
    return str(uuid.uuid5(_QDRANT_NAMESPACE, entry_id))

openai = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
qdrant = AsyncQdrantClient(url=os.environ.get("QDRANT_URL", "http://localhost:6333"))


async def ensure_collection():
    """Idempotent — call on app startup."""
    collections = await qdrant.get_collections()
    if not any(c.name == COLLECTION for c in collections.collections):
        await qdrant.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
        )


async def embed_text(text: str) -> list[float]:
    """Return a single embedding vector."""
    response = await openai.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )
    return response.data[0].embedding


async def index_entry(entry_id: str, user_id: str, content: str, created_at_iso: str):
    """Embed + upsert into Qdrant. Updates the entry's embedding_status on success/failure."""
    from models.entry import Entry  # local import avoids a circular import at module load
    from beanie import PydanticObjectId

    try:
        vector = await embed_text(content)
        await qdrant.upsert(
            collection_name=COLLECTION,
            points=[
                PointStruct(
                    id=to_point_id(entry_id),
                    vector=vector,
                    payload={
                        "user_id": user_id,
                        "entry_id": entry_id,
                        "created_at": created_at_iso,
                        "preview": content[:200],
                    },
                )
            ],
        )
        status = "indexed"
    except Exception as e:
        print(f"⚠️  Failed to index entry {entry_id}: {e}")
        status = "failed"

    entry = await Entry.get(PydanticObjectId(entry_id))
    if entry:
        entry.embedding_status = status
        await entry.save()


async def search(user_id: str, query: str, limit: int = 5) -> list[dict]:
    """Semantic search scoped to a single user.

    The user_id filter is critical for security: we run on a single shared collection,
    so the filter ensures users only see their own entries.
    """
    query_vector = await embed_text(query)
    results = await qdrant.search(
        collection_name=COLLECTION,
        query_vector=query_vector,
        query_filter=Filter(
            must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
        ),
        limit=limit,
    )
    return [
        {
            "entry_id": r.payload["entry_id"],
            "preview": r.payload["preview"],
            "created_at": r.payload["created_at"],
            "score": r.score,  # cosine similarity, higher = more relevant
        }
        for r in results
    ]


async def delete_entry(entry_id: str):
    await qdrant.delete(collection_name=COLLECTION, points_selector=[to_point_id(entry_id)])