"""Snapshot priority (chapter 07): the card rule, applied to the best candidate a procedure page mentions."""

from __future__ import annotations

import pytest
from app.features.translation.priority import (
    RETRANSLATION_BASE,
    snapshot_first_priority,
    snapshot_retranslation_priority,
)
from app.models.fair_selection_state import FairSelectionState
from sqlalchemy.orm import Session


def test_a_first_translation_has_base_zero_and_a_retranslation_base_ten_thousand() -> None:
    """priority · a first translation has base 0 and a re-translation base 10,000 at the same confidence."""
    assert snapshot_first_priority([1.0]) == 0
    assert snapshot_retranslation_priority([1.0]) == RETRANSLATION_BASE == 10_000


def test_a_higher_confidence_ranks_earlier_and_every_first_translation_ranks_before_any_retranslation() -> None:
    """priority · higher confidence ranks earlier, and a first translation ranks before any re-translation."""
    assert snapshot_first_priority([0.9]) < snapshot_first_priority([0.2])
    assert snapshot_first_priority([0.0]) < snapshot_retranslation_priority([1.0])


def test_a_page_ranks_by_its_highest_candidate_confidence_and_a_page_without_candidates_ranks_last() -> None:
    """priority · a page takes the highest confidence among the candidates it mentions; none means the lowest rank."""
    assert snapshot_first_priority([0.1, 0.9]) == snapshot_first_priority([0.9])
    assert snapshot_retranslation_priority([0.1, 0.9]) == snapshot_retranslation_priority([0.9])
    assert snapshot_first_priority([]) == snapshot_first_priority([0.0])


# Slice 2: Compute Page Confidence (Max of Mentioning Candidates)
def test_page_confidence_returns_max_of_candidate_scores() -> None:
    """priority · page confidence is the maximum of candidate scores."""
    from app.features.translation.priority import page_confidence

    assert page_confidence([0.5, 0.9, 0.3]) == 0.9
    assert page_confidence([0.1, 0.1]) == 0.1
    assert page_confidence([0.9]) == 0.9


def test_page_confidence_returns_zero_when_no_candidates() -> None:
    """priority · page with no candidates has confidence 0.0."""
    from app.features.translation.priority import page_confidence

    assert page_confidence([]) == 0.0


# Slice 3: Modify Snapshot Priority Functions to Include Phase Component
def test_snapshot_first_priority_includes_phase_band() -> None:
    """priority · phase 1 band (0–99,999) ranks before phase 2 band (100,000–199,999)."""
    priority_p1 = snapshot_first_priority([0.9], phase=1)
    priority_p2 = snapshot_first_priority([0.9], phase=2)

    # Phase 1 should be in band 0–99,999
    assert 0 <= priority_p1 < 100_000, f"Phase 1 priority {priority_p1} not in band 0–99,999"
    # Phase 2 should be in band 100,000–199,999
    assert 100_000 <= priority_p2 < 200_000, f"Phase 2 priority {priority_p2} not in band 100,000–199,999"
    # Phase 1 should always rank before phase 2
    assert priority_p1 < priority_p2, f"Phase 1 priority {priority_p1} should be < phase 2 priority {priority_p2}"


def test_snapshot_first_priority_preserves_confidence_order_within_phase() -> None:
    """priority · within the same phase, higher confidence ranks earlier."""
    high_conf_p1 = snapshot_first_priority([0.9], phase=1)
    low_conf_p1 = snapshot_first_priority([0.3], phase=1)

    # High confidence should rank before low confidence within phase 1
    assert high_conf_p1 < low_conf_p1, (
        f"High confidence {high_conf_p1} should rank before low confidence {low_conf_p1} in phase 1"
    )
