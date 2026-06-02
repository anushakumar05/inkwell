"""
Tests for the MoodAnalysis schema.

We test the SCHEMA's validation rules (not the live LLM call, which costs money and
is non-deterministic). This confirms our data contract rejects out-of-range values —
important because charts and aggregations assume scores are within [-1, 1].
"""
import pytest
from pydantic import ValidationError
from models.entry import MoodAnalysis


def test_valid_mood_passes():
    m = MoodAnalysis(valence=0.5, energy=-0.3, dominant_emotion="content",
                     themes=["rest"], confidence=0.9)
    assert m.valence == 0.5


def test_valence_out_of_range_rejected():
    with pytest.raises(ValidationError):
        MoodAnalysis(valence=1.5, energy=0.0, dominant_emotion="x",
                     themes=[], confidence=0.5)


def test_confidence_out_of_range_rejected():
    with pytest.raises(ValidationError):
        MoodAnalysis(valence=0.0, energy=0.0, dominant_emotion="x",
                     themes=[], confidence=2.0)