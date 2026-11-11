"""Canonical list-query allowlist of the public candidate list and its mapping to a ``PublicCandidateFilter``."""

from __future__ import annotations

import enum
from dataclasses import replace

from app.features.candidates.repository import PublicCandidateFilter, PublicSortKey
from app.shared.list_query import FilterValue, ListQuery, ListQuerySpec, SortOrder, enum_filter
from app.shared.retired_taxonomy import RETIRED_TAXONOMY_AXES

CODE_MAX_LENGTH = 64
CODES_MAX_COUNT = 20


class CompleteChoice(enum.StrEnum):
    """Values of ``filter[complete]``."""

    YES = "yes"
    NO = "no"


def _checked_items(raw: str) -> list[str]:
    """Split ``raw`` on commas into trimmed codes, each of 1 to 64 characters; at most 20 of them."""
    items = [item.strip() for item in raw.split(",")]
    if len(items) > CODES_MAX_COUNT:
        raise ValueError(f"Expected at most {CODES_MAX_COUNT} codes")
    if not all(1 <= len(item) <= CODE_MAX_LENGTH for item in items):
        raise ValueError(f"Expected comma-separated codes of 1 to {CODE_MAX_LENGTH} characters")
    return items


def codes_filter(raw: str) -> FilterValue:
    """Accept a CSV of taxonomy codes and return it trimmed and de-duplicated; the service checks the taxonomy."""
    return ",".join(dict.fromkeys(_checked_items(raw)))


def _codes(query: ListQuery, name: str) -> tuple[str, ...]:
    """Return the codes of the CSV filter ``name``, or none when it is not set."""
    value = query.filter_value(name, str)
    return () if value is None else tuple(value.split(","))


PUBLIC_CANDIDATE_SPEC = ListQuerySpec(
    sort_keys=frozenset(key.value for key in PublicSortKey),
    filters={
        "complete": enum_filter(CompleteChoice),
        "category": codes_filter,
    },
    retired_filters=RETIRED_TAXONOMY_AXES,
)


def public_filter_from(query: ListQuery) -> PublicCandidateFilter:
    """Return the filter for ``query``; without ``sort_by`` the list is ranked by the combined score, best first."""
    complete = query.filter_value("complete", CompleteChoice)
    narrowed = PublicCandidateFilter(
        complete=None if complete is None else complete is CompleteChoice.YES,
        category_codes=_codes(query, "category"),
        q=query.q,
    )
    if query.sort_by is None:
        return narrowed
    return replace(narrowed, sort_by=PublicSortKey(query.sort_by), sort_order=query.sort_order or SortOrder.ASC)
