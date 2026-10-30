"""Filter options and ordering of the public candidate list."""

from __future__ import annotations

import enum
from dataclasses import dataclass

from sqlalchemy import ColumnElement, String, any_, literal
from sqlalchemy.sql.expression import Subquery

from app.features.discovery.repository.candidate_completeness import completeness_order
from app.features.discovery.repository.candidate_filter import title_matches, when
from app.features.discovery.repository.candidate_sort import (
    CandidateSortKey,
    MentionCount,
    Ordering,
    candidate_ordering,
    tie_break,
)
from app.shared.list_query import SortOrder


class PublicSortKey(enum.StrEnum):
    """Public sort fields: the admin keys plus completeness."""

    COMPLETENESS = "completeness"
    MENTIONS = "mentions"
    TITLE = "title"
    CREATED_AT = "created_at"


def _accepted(code: str, accepted_codes: ColumnElement) -> ColumnElement[bool]:
    """Return a predicate that ``code`` is one of the accepted codes array (a ``NULL`` array accepts nothing)."""
    return literal(code, String) == any_(accepted_codes)


@dataclass(frozen=True, slots=True)
class PublicCandidateFilter:
    """Optional narrowing and ordering of one public listing; the default is the ranked list."""

    complete: bool | None = None
    domain: str | None = None
    situation: str | None = None
    q: str | None = None
    sort_by: PublicSortKey = PublicSortKey.COMPLETENESS
    sort_order: SortOrder = SortOrder.DESC

    def conditions(self, completeness: Subquery) -> list[ColumnElement[bool]]:
        """Return the where-clauses of the filters that are set; codes must be accepted ones."""
        return [
            *when(self.complete, lambda value: completeness.c.complete.is_(value)),
            *when(self.domain, lambda code: _accepted(code, completeness.c.accepted_domain_codes)),
            *when(self.situation, lambda code: _accepted(code, completeness.c.accepted_situation_codes)),
            *when(self.q, title_matches),
        ]

    def ordering(self, completeness: Subquery, mention_count: MentionCount) -> Ordering:
        """Return the order-by clauses of the chosen sort, always ending in the deterministic tie-break."""
        if self.sort_by is PublicSortKey.COMPLETENESS:
            return (*completeness_order(completeness, mention_count, self.sort_order), *tie_break())
        return candidate_ordering(CandidateSortKey(self.sort_by.value), self.sort_order, mention_count)
