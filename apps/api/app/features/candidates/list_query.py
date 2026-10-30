"""Canonical list-query allowlist of the public candidate list and its mapping to a ``PublicCandidateFilter``."""

from __future__ import annotations

import enum
from dataclasses import replace

from app.features.candidates.repository import PublicCandidateFilter, PublicSortKey
from app.shared.list_query import FilterValue, ListQuery, ListQuerySpec, SortOrder, enum_filter

CODE_MAX_LENGTH = 64


class CompleteChoice(enum.StrEnum):
    """Values of ``filter[complete]``."""

    YES = "yes"
    NO = "no"


def _code_filter(raw: str) -> FilterValue:
    """Accept a taxonomy code of 1 to 64 characters; the service checks it against the closed taxonomy."""
    if not 1 <= len(raw) <= CODE_MAX_LENGTH:
        raise ValueError(f"Expected 1 to {CODE_MAX_LENGTH} characters")
    return raw


PUBLIC_CANDIDATE_SPEC = ListQuerySpec(
    sort_keys=frozenset(key.value for key in PublicSortKey),
    filters={"complete": enum_filter(CompleteChoice), "domain": _code_filter, "situation": _code_filter},
)


def public_filter_from(query: ListQuery) -> PublicCandidateFilter:
    """Return the filter for ``query``; without ``sort_by`` the list is ranked by completeness, best first."""
    complete = query.filter_value("complete", CompleteChoice)
    narrowed = PublicCandidateFilter(
        complete=None if complete is None else complete is CompleteChoice.YES,
        domain=query.filter_value("domain", str),
        situation=query.filter_value("situation", str),
        q=query.q,
    )
    if query.sort_by is None:
        return narrowed
    return replace(narrowed, sort_by=PublicSortKey(query.sort_by), sort_order=query.sort_order or SortOrder.ASC)
