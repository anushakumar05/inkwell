"""
Mood extraction service.

Uses OpenAI's structured-output parsing (`chat.completions.parse`), which takes a
Pydantic model directly and GUARANTEES the response matches that schema. This is the
production pattern for turning unstructured text into reliable structured data: the
model literally cannot return a shape that violates the contract.

Model choice — gpt-4o-mini:
  1. Mood extraction is a classification-shaped task; the big model is overkill.
  2. Cost: ~$0.0001 per entry. Thousands of entries for pennies.
  3. Latency: <1s, and it runs in the background anyway.
"""
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

from models.entry import MoodAnalysis

openai = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])

SYSTEM_PROMPT = """You analyze journal entries for emotional content.

Return a structured analysis with:
- valence: a number indicating positive (+1) or negative (-1) the entry feels overall - number should be in range [-1,1]
- energy: how activated/high-energy/passionate (+1) or calm/low-energy/disinterested/indifferent (-1) the writer is - number should be in range [-1,1]
- dominant_emotion: a single word for the main feeling (e.g. "anxious", "content", "frustrated", "grateful", "lonely")
- themes: 1-4 short noun phrases capturing what the entry is ABOUT (e.g. "work stress", "family conflict", "creative breakthrough")
- confidence: how confident you are in this analysis (0-1). Lower for ambiguous or very short entries.

Be honest about ambiguity. Do not pathologize normal emotions. Do not project emotions the writer did not express.
"""


async def extract_mood(content: str) -> MoodAnalysis:
    """Returns a validated MoodAnalysis. Raises if the API call fails."""
    completion = await openai.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Analyze this journal entry:\n\n{content}"},
        ],
        response_format=MoodAnalysis,
        temperature=0.2,
    )
    return completion.choices[0].message.parsed