"""In-batch catalogue deduplication before machine API POST."""

from __future__ import annotations

import uuid

from discovery_ingest.batch_dedup import dedupe_batch_items
from discovery_ingest.schemas import CatalogueBatchItem

_JURISDICTION = uuid.uuid4()


def _item(external_id: str, **title: str) -> CatalogueBatchItem:
    return CatalogueBatchItem(
        source="govdata",
        external_id=external_id,
        jurisdiction_id=_JURISDICTION,
        title_i18n=title or {"de": external_id},
    )


def test_dedupe_batch_items_keeps_last_duplicate_by_source_and_external_id() -> None:
    """dedupe_batch_items · keeps last row per (source, external_id)."""
    first = _item("dup-a", de="first")
    second = _item("dup-a", de="second")
    third = _item("other", de="solo")

    result = dedupe_batch_items([first, second, third])

    assert len(result) == 2
    assert result[0].external_id == "dup-a"
    assert result[0].title_i18n["de"] == "second"
    assert result[1].external_id == "other"


def test_dedupe_batch_items_rejects_empty_sequence() -> None:
    """dedupe_batch_items · rejects empty input."""
    try:
        dedupe_batch_items([])
    except ValueError as err:
        assert "empty" in str(err).lower()
    else:
        raise AssertionError("expected ValueError for empty items")
