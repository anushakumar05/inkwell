"""
One-time fix: spread existing entries' created_at dates backward over the past few weeks.
Useful when entries were all inserted at once (same timestamp) and you want a realistic
timeline for the mood chart.

Usage: python -m scripts.respace_dates
"""
import asyncio
import random
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from dotenv import load_dotenv
import os

load_dotenv()
from models.entry import Entry


async def main():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    await init_beanie(database=client[os.environ["DB_NAME"]], document_models=[Entry])

    # Oldest-first, by current insertion order (Mongo ObjectIds encode creation time).
    entries = await Entry.find_all().sort(Entry.id).to_list()
    print(f"Re-spacing {len(entries)} entries...")

    # Walk backward from today. Each entry lands 1-3 days before the previous one,
    # at a random hour, so the timeline looks naturally uneven rather than perfectly spaced.
    cursor = datetime.utcnow()
    # Reverse so the NEWEST entry (last inserted) stays closest to today.
    for entry in reversed(entries):
        hour = random.randint(7, 23)
        minute = random.randint(0, 59)
        dt = cursor.replace(hour=hour, minute=minute, second=0, microsecond=0)
        entry.created_at = dt
        entry.updated_at = dt
        await entry.save()
        print(f"  ✓ {dt.strftime('%Y-%m-%d %H:%M')}  {entry.content[:45]}...")
        # Step back 1-3 days for the next (older) entry
        cursor = dt - timedelta(days=random.randint(1, 3))

    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())