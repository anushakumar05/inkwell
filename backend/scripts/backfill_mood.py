"""
One-time backfill: extract mood for all entries that don't have it yet.
Run after adding mood extraction, or to re-process entries.

Usage: python -m scripts.backfill_mood
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from dotenv import load_dotenv
import os

load_dotenv()
from models.entry import Entry
from services.mood import extract_mood


async def main():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    await init_beanie(database=client[os.environ["DB_NAME"]], document_models=[Entry])

    entries = await Entry.find_all().to_list()
    todo = [e for e in entries if e.mood is None]
    print(f"{len(todo)} of {len(entries)} entries need mood analysis...")

    for entry in todo:
        try:
            entry.mood = await extract_mood(entry.content)
            await entry.save()
            print(f"  ✓ {entry.mood.dominant_emotion:12} (v={entry.mood.valence:+.2f})  {entry.content[:40]}...")
        except Exception as e:
            print(f"  ✗ failed on {entry.id}: {e}")

    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())