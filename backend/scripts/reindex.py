"""
One-time backfill: embed all existing entries into Qdrant.
Run when you first add embeddings, or any time Qdrant and Mongo drift apart.

Usage: python -m scripts.reindex
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from dotenv import load_dotenv
import os

load_dotenv()
from models.entry import Entry
from services.embeddings import ensure_collection, index_entry


async def main():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    await init_beanie(database=client[os.environ["DB_NAME"]], document_models=[Entry])
    await ensure_collection()

    entries = await Entry.find_all().to_list()
    print(f"Re-indexing {len(entries)} entries...")
    for entry in entries:
        await index_entry(
            entry_id=str(entry.id),
            user_id=entry.user_id,
            content=entry.content,
            created_at_iso=entry.created_at.isoformat(),
        )
        print(f"  ✓ {str(entry.id)[:8]}... ({entry.word_count} words)")
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())