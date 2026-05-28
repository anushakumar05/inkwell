import asyncio
from dotenv import load_dotenv
load_dotenv()
from services.embeddings import embed_text

async def main():
    vec = await embed_text("I felt overwhelmed at work today")
    print(f"Got embedding with {len(vec)} dimensions")
    print(f"First 5 numbers: {vec[:5]}")

asyncio.run(main())