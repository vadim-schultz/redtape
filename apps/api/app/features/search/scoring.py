"""The combined ranking score: relevance and confidence blended by one weight, in Python and in SQL.

This module is the only place that does the arithmetic; orderings and cards call it.
"""

from __future__ import annotations

from typing import Final

from sqlalchemy import ColumnElement

SCORE_DECIMALS: Final = 4
"""Decimals of the score a card shows; ordering reads the unrounded value."""


def _checked(weight: float) -> float:
    """Return ``weight`` when it lies in 0..1, else raise :class:`ValueError`."""
    if not 0.0 <= weight <= 1.0:
        raise ValueError(f"The confidence weight must lie in 0..1, got {weight}")
    return weight


def combined_score(relevance: float, confidence: float, weight: float) -> float:
    """Return ``(1 - weight) * relevance + weight * confidence``, the reference of :func:`combined_expression`."""
    share = _checked(weight)
    return (1.0 - share) * relevance + share * confidence


def combined_expression(
    relevance: ColumnElement[float], confidence: ColumnElement[float], weight: float
) -> ColumnElement[float]:
    """Return the SQL of :func:`combined_score` over a relevance and a confidence column."""
    share = _checked(weight)
    return relevance * (1.0 - share) + confidence * share


def displayed_score(score: float) -> float:
    """Return ``score`` rounded to the decimals a card shows."""
    return round(score, SCORE_DECIMALS)
