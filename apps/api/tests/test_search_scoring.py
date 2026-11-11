"""``features/search/scoring``: the combined relevance and confidence score, as a function and as SQL."""

from __future__ import annotations

import itertools

import pytest
from app.features.search.scoring import combined_expression, combined_score
from sqlalchemy import Float, cast, literal, select
from sqlalchemy.orm import Session

GRID = (0.0, 0.25, 0.5, 0.8, 1.0)


@pytest.mark.parametrize(
    ("relevance", "confidence", "weight", "expected"),
    [
        (1.0, 0.0, 0.3, 0.7),
        (0.5, 1.0, 0.3, 0.65),
        (0.5, 0.0, 0.3, 0.35),
        (1.0, 1.0, 0.3, 1.0),
        (0.0, 0.0, 0.3, 0.0),
    ],
    ids=["keyword best match", "hybrid single-leg best match", "hybrid single leg unsupported", "both", "neither"],
)
def test_scoring_combines_relevance_and_confidence_with_the_weight(
    relevance: float, confidence: float, weight: float, expected: float
) -> None:
    """scoring · combines relevance and confidence with the weight (hybrid 0.5 and keyword 1.0 normalisation)."""
    assert combined_score(relevance, confidence, weight) == pytest.approx(expected)


def test_weight_one_is_the_confidence_and_weight_zero_is_the_relevance() -> None:
    """scoring · the weight extremes reproduce confidence-first and pure relevance."""
    assert combined_score(0.9, 0.2, 1.0) == pytest.approx(0.2)
    assert combined_score(0.9, 0.2, 0.0) == pytest.approx(0.9)


@pytest.mark.parametrize("weight", [-0.01, 1.01])
def test_a_weight_outside_zero_to_one_is_rejected_by_both_implementations(weight: float) -> None:
    """scoring · a weight outside 0..1 raises ValueError in the reference and in the SQL expression."""
    with pytest.raises(ValueError, match="weight"):
        combined_score(0.5, 0.5, weight)
    with pytest.raises(ValueError, match="weight"):
        combined_expression(literal(0.5), literal(0.5), weight)


def test_the_sql_expression_and_the_python_reference_agree(db_session: Session) -> None:
    """scoring · SQL expression and Python reference agree over a grid of relevance, confidence and weight."""
    for relevance, confidence, weight in itertools.product(GRID, GRID, (0.0, 0.3, 0.7, 1.0)):
        expression = combined_expression(cast(literal(relevance), Float), cast(literal(confidence), Float), weight)
        in_sql = db_session.scalar(select(expression))
        assert in_sql == pytest.approx(combined_score(relevance, confidence, weight)), (relevance, confidence, weight)
