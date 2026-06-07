"""
Tests for the EvalScores schema validation.
The judge's runtime behavior we don't test (live LLM call, costs money), but
the score schema must reject out-of-range values to protect the dashboard math.
"""
import pytest
from pydantic import ValidationError
from services.evaluation import EvalScores


def test_valid_scores_pass():
    s = EvalScores(faithfulness=0.85, answer_relevance=0.9, context_relevance=0.75, notes="ok")
    assert s.faithfulness == 0.85


def test_faithfulness_out_of_range_rejected():
    with pytest.raises(ValidationError):
        EvalScores(faithfulness=1.2, answer_relevance=0.5, context_relevance=0.5, notes="")


def test_negative_score_rejected():
    with pytest.raises(ValidationError):
        EvalScores(faithfulness=-0.1, answer_relevance=0.5, context_relevance=0.5, notes="")


def test_all_three_scores_required():
    with pytest.raises(ValidationError):
        # Missing context_relevance
        EvalScores(faithfulness=0.5, answer_relevance=0.5, notes="")