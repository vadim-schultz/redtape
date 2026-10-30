"""Orderings of the admin candidate listing: a public sort key plus a direction, always tie-broken."""

from __future__ import annotations

import enum
from collections.abc import Callable, Mapping

from sqlalchemy import ColumnElement, func

from app.models.discovery import DiscoveryDocumentCandidate as Candidate
from app.shared.list_query import SortOrder

MentionCount = ColumnElement[int]
Ordering = tuple[ColumnElement, ...]


class CandidateSortKey(enum.StrEnum):
    """Public sort fields of the candidate list."""

    MENTIONS = "mentions"
    TITLE = "title"
    CREATED_AT = "created_at"


class CandidateSort(enum.StrEnum):
    """Legacy combined ``sort`` values, kept as an alias of a key and direction."""

    MENTIONS_DESC = "mentions_desc"
    TITLE_ASC = "title_asc"
    NEWEST = "newest"


LEGACY_SORTS: Mapping[CandidateSort, tuple[CandidateSortKey, SortOrder]] = {
    CandidateSort.MENTIONS_DESC: (CandidateSortKey.MENTIONS, SortOrder.DESC),
    CandidateSort.TITLE_ASC: (CandidateSortKey.TITLE, SortOrder.ASC),
    CandidateSort.NEWEST: (CandidateSortKey.CREATED_AT, SortOrder.DESC),
}


def title_expression() -> ColumnElement[str]:
    """Return the lower-cased German, else English, else key title used for ordering."""
    german, english = Candidate.title_i18n["de"].as_string(), Candidate.title_i18n["en"].as_string()
    return func.lower(func.coalesce(german, english, Candidate.key))


_PRIMARY: Mapping[CandidateSortKey, Callable[[MentionCount], ColumnElement]] = {
    CandidateSortKey.MENTIONS: lambda count: count,
    CandidateSortKey.TITLE: lambda _count: title_expression(),
    CandidateSortKey.CREATED_AT: lambda _count: Candidate.created_at.expression,
}


def tie_break() -> Ordering:
    """Return the deterministic tail of every candidate ordering: title, key and id ascending."""
    return (title_expression().asc(), Candidate.key.asc(), Candidate.id.asc())


def candidate_ordering(key: CandidateSortKey, order: SortOrder, mention_count: MentionCount) -> Ordering:
    """Return the order-by clauses: the requested key and direction, then the :func:`tie_break`."""
    primary = _PRIMARY[key](mention_count)
    directed = primary.desc() if order is SortOrder.DESC else primary.asc()
    return (directed, *tie_break())
