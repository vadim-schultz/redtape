"""Snapshot priority (chapter 07): the card rule, applied to the best candidate a procedure page mentions."""

from __future__ import annotations

from app.features.translation.priority import (
    RETRANSLATION_BASE,
    snapshot_first_priority,
    snapshot_retranslation_priority,
)


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
