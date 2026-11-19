"""The spend of the last day, summed per budget resource and per run stage."""

from __future__ import annotations

from collections.abc import Iterable, Iterator


def _entries(rows: Iterable[tuple[str, dict[str, float] | None]]) -> Iterator[tuple[str, str, float]]:
    return ((stage, resource, amount) for stage, spend in rows for resource, amount in (spend or {}).items())


def spend_by_resource(rows: Iterable[tuple[str, dict[str, float] | None]]) -> dict[str, dict[str, float]]:
    """Return ``{resource: {run stage: amount}}`` summed over ``rows``; a run that recorded no spend adds nothing."""
    totals: dict[str, dict[str, float]] = {}
    for stage, resource, amount in _entries(rows):
        by_stage = totals.setdefault(resource, {})
        by_stage[stage] = by_stage.get(stage, 0.0) + amount
    return totals
