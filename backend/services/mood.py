"""
Mood extraction service.

Uses structured outputs (Pydantic schema → JSON Schema → enforced by the LLM).
This is one of the most important production AI patterns to demonstrate:
unstructured LLM output is unreliable, structured output is contract-bound.

We use gpt-4o-mini here because:
  1. Mood extraction is a simple classification-shaped task; you don't need the big model.
  2. Cost: ~$0.0001 per entry. You can process thousands of entries for pennies.
  3. Latency: <1s, so it doesn't bottleneck the UI.
"""
import os
import json
from openai import AsyncOpenAI
from models.entry import MoodAnalysis

openai = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])

SYSTEM_PROMPT = """You analyze journal entries for emotional content.

Return a structured analysis with:
- valence: how positive (+1) or negative (-1) the entry feels overall
- energy: how activated/high-energy (+1) or calm/low-energy (-1) the writer is
- dominant_emotion: a single word describing the main feeling (e.g. "anxious", "content", "frustrated", "grateful", "lonely")
- themes: 1-4 short noun phrases capturing what the entry is ABOUT (e.g. "work stress", "family conflict", "creative breakthrough")
- confidence: how confident you are in this analysis (0-1). Lower for ambiguous or short entries.

Be honest about ambiguity. Do not pathologize normal emotions. Do not project emotions the writer did not express.
"""


async def extract_mood(content: str) -> MoodAnalysis:
    """Returns a validated MoodAnalysis or raises on schema violation."""
    response = await openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Analyze this journal entry:\n\n{content}"},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "mood_analysis",
                "schema": MoodAnalysis.model_json_schema(),
                "strict": True,
            },
        },
        temperature=0.2,  # low temp for consistency across re-runs of the same entry
    )
    raw = response.choices[0].message.content
    return MoodAnalysis.model_validate_json(raw)
