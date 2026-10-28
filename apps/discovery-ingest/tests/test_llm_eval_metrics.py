"""The eval metrics as pure functions on plain data (chapter E5, loop A)."""

from __future__ import annotations

import pytest
from discovery_ingest.extract.llm.evaluation.metrics import (
    Counts,
    document_counts,
    edge_counts,
    grounded_rate,
    tag_agreement,
)


def test_precision_and_recall_count_matching_slug_and_role_and_ignore_order() -> None:
    """document_counts · the slug of the name and the role must both match; order and case do not matter."""
    predicted = [("Reisepass", "required"), ("Meldebescheinigung", "form"), ("Phantom", "required")]
    gold = [("meldebescheinigung", "required"), ("REISEPASS", "required"), ("Personalausweis", "required")]

    counts = document_counts(predicted, gold)

    assert counts == Counts(correct=1, predicted=3, gold=3)
    assert counts.precision == pytest.approx(1 / 3)
    assert counts.recall == pytest.approx(1 / 3)


def test_counts_add_up_so_pages_can_be_pooled() -> None:
    """Counts · adding two pages sums the three tallies and the pooled scores follow from the sums."""
    pooled = Counts(1, 2, 4) + Counts(2, 2, 2)

    assert pooled == Counts(3, 4, 6)
    assert pooled.precision == 0.75 and pooled.recall == 0.5


def test_edge_scoring_uses_parent_and_required_slugs() -> None:
    """edge_counts · the pair must match in direction; a reversed edge is a miss."""
    predicted = [("Antrag", "Personalausweis"), ("Personalausweis", "Antrag"), ("Antrag", "Foto")]
    gold = [("antrag", "PERSONALAUSWEIS"), ("Antrag", "Meldebescheinigung")]

    assert edge_counts(predicted, gold) == Counts(correct=1, predicted=3, gold=2)


def test_grounded_rate_is_surviving_items_over_raw_items() -> None:
    """grounded_rate · three of four raw items surviving is 0.75; no raw items is a full rate; more survivors is refused."""
    assert grounded_rate(raw_items=4, kept_items=3) == 0.75
    assert grounded_rate(raw_items=0, kept_items=0) == 1.0
    with pytest.raises(ValueError, match="more items kept than raw"):
        grounded_rate(raw_items=1, kept_items=2)


def test_tag_agreement_is_the_mean_jaccard_and_treats_empty_against_empty_as_agreement() -> None:
    """tag_agreement · pages average their Jaccard overlap; empty against empty is 1 and empty against codes is 0."""
    pages = [
        (["housing"], ["housing"]),
        (["housing", "work-employment"], ["housing"]),
        ([], []),
        ([], ["moving-house"]),
    ]

    assert tag_agreement(pages) == pytest.approx((1 + 0.5 + 1 + 0) / 4)
    assert tag_agreement([]) == 1.0


def test_a_page_with_no_gold_documents_and_no_predictions_scores_as_correct_not_as_a_division_by_zero() -> None:
    """document_counts · nothing expected and nothing found is precision and recall 1; inventing a document is not."""
    quiet = document_counts([], [])
    invented = document_counts([("Phantom", "required")], [])

    assert quiet == Counts(0, 0, 0)
    assert quiet.precision == 1.0 and quiet.recall == 1.0
    assert invented.precision == 0.0 and invented.recall == 1.0
