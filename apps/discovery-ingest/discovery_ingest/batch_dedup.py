"""Collapse duplicate catalogue rows before machine API batch POST."""

from __future__ import annotations

from collections.abc import Sequence

from discovery_ingest.schemas import CatalogueBatchItem


def dedupe_batch_items(items: Sequence[CatalogueBatchItem]) -> list[CatalogueBatchItem]:
    """Return ``items`` with at most one row per ``(source, external_id)`` (last wins)."""

    if not items:
        raise ValueError("items must not be empty")
    by_key: dict[tuple[str, str], CatalogueBatchItem] = {}
    order: list[tuple[str, str]] = []
    for item in items:
        key = (item.source, item.external_id)
        if key not in by_key:
            order.append(key)
        by_key[key] = item
    return [by_key[key] for key in order]
