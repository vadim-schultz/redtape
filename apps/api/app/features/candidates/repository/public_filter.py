"""Filter options and ordering of the public candidate list."""

from __future__ import annotations

import enum
from dataclasses import dataclass

from sqlalchemy import ColumnElement, exists, literal, select
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
from app.features.discovery.tags import TagAxis
from app.models.discovery import DiscoveryDocumentCandidate as Candidate
from app.shared.list_query import SortOrder


class PublicSortKey(enum.StrEnum):
    """Public sort fields: the admin keys plus completeness."""

    COMPLETENESS = "completeness"
    MENTIONS = "mentions"
    TITLE = "title"
    CREATED_AT = "created_at"


def _present(scores: Subquery, axis: TagAxis, codes: tuple[str, ...]) -> ColumnElement[bool]:
    """Return a predicate that the candidate has a score on ``axis`` for any of ``codes``, whatever its value."""
    match = select(literal(1)).where(
        scores.c.candidate_id == Candidate.id, scores.c.axis == axis.value, scores.c.code.in_(codes)
    )
    return exists(match)


@dataclass(frozen=True, slots=True)
class PublicCandidateFilter:
    """Optional narrowing and ordering of one public listing; the default is the ranked list."""

    complete: bool | None = None
    domains: tuple[str, ...] = ()
    situations: tuple[str, ...] = ()
    q: str | None = None
    sort_by: PublicSortKey = PublicSortKey.COMPLETENESS
    sort_order: SortOrder = SortOrder.DESC

    def conditions(self, completeness: Subquery, scores: Subquery) -> list[ColumnElement[bool]]:
        """Return the where-clauses of the filters that are set: a code matches by presence in ``scores``."""
        return [
            *when(self.complete, lambda value: completeness.c.complete.is_(value)),
            *when(self.domains or None, lambda codes: _present(scores, TagAxis.DOMAIN, codes)),
            *when(self.situations or None, lambda codes: _present(scores, TagAxis.SITUATION, codes)),
            *when(self.q, title_matches),
        ]

    def ordering(self, completeness: Subquery, mention_count: MentionCount) -> Ordering:
        """Return the order-by clauses of the chosen sort, always ending in the deterministic tie-break."""
        if self.sort_by is PublicSortKey.COMPLETENESS:
            return (*completeness_order(completeness, mention_count, self.sort_order), *tie_break())
        return candidate_ordering(CandidateSortKey(self.sort_by.value), self.sort_order, mention_count)
