"""Tests for `decide_status`, the pure score-to-status rule (Chapter 4)."""

from __future__ import annotations

import pytest
from app.features.voting.thresholds import decide_status
from app.models.suggestion import SuggestionStatus


@pytest.mark.parametrize("score", [-2, -1, 0, 1, 2])
def test_below_both_thresholds_stays_pending(score: int) -> None:
    assert decide_status(score, approve=3, reject=-3) == SuggestionStatus.PENDING


@pytest.mark.parametrize("score", [3, 4])
def test_at_or_above_the_approve_threshold_is_approved(score: int) -> None:
    assert decide_status(score, approve=3, reject=-3) == SuggestionStatus.APPROVED


@pytest.mark.parametrize("score", [-3, -4])
def test_at_or_below_the_reject_threshold_is_rejected(score: int) -> None:
    assert decide_status(score, approve=3, reject=-3) == SuggestionStatus.REJECTED
