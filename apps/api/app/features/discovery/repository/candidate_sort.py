"""Orderings of the admin candidate listing: a public sort key plus a direction, always tie-broken."""

from __future__ import annotations

import enum
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from sqlalchemy import ColumnElement, func, null

from app.features.discovery.repository.candidate_sort_expressions import (
    jurisdiction_name_expression,
    role_count_expression,
    role_set_expression,
)
from app.models.discovery import DiscoveryDocumentCandidate as Candidate
from app.shared.list_query import SortOrder

MentionCount = ColumnElement[int]
Ordering = tuple[ColumnElement, ...]


class CandidateSortKey(enum.StrEnum):
    """Public sort fields of the candidate list."""

    MENTIONS = "mentions"
    TITLE = "title"
    CREATED_AT = "created_at"
    JURISDICTION = "jurisdiction"
    STATUS = "status"
    ROLES = "roles"
    COMPLETENESS = "completeness"


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


@dataclass(frozen=True, slots=True)
class SortInputs:
    """The columns besides the candidate's own that an ordering reads; unused ones stay ``NULL``."""

    mention_count: MentionCount
    roles: ColumnElement = field(default_factory=null)
    completeness: ColumnElement = field(default_factory=null)


_PRIMARY: Mapping[CandidateSortKey, Callable[[SortInputs], Ordering]] = {
    CandidateSortKey.MENTIONS: lambda inputs: (inputs.mention_count,),
    CandidateSortKey.TITLE: lambda _inputs: (title_expression(),),
    CandidateSortKey.CREATED_AT: lambda _inputs: (Candidate.created_at.expression,),
    CandidateSortKey.JURISDICTION: lambda _inputs: (jurisdiction_name_expression(),),
    CandidateSortKey.STATUS: lambda _inputs: (Candidate.status.expression,),
    CandidateSortKey.ROLES: lambda inputs: (role_count_expression(inputs.roles), role_set_expression(inputs.roles)),
    CandidateSortKey.COMPLETENESS: lambda inputs: (inputs.completeness,),
}


def tie_break() -> Ordering:
    """Return the deterministic tail of every candidate ordering: title, key and id ascending."""
    return (title_expression().asc(), Candidate.key.asc(), Candidate.id.asc())


def ordered_by(key: CandidateSortKey, order: SortOrder, inputs: SortInputs) -> Ordering:
    """Return the order-by clauses: ``key`` in direction ``order``, then the :func:`tie_break`."""
    primary = _PRIMARY[key](inputs)
    directed = tuple(column.desc() if order is SortOrder.DESC else column.asc() for column in primary)
    return (*directed, *tie_break())


def candidate_ordering(key: CandidateSortKey, order: SortOrder, mention_count: MentionCount) -> Ordering:
    """Return the order-by clauses of a key that reads only the mention count."""
    return ordered_by(key, order, SortInputs(mention_count))
