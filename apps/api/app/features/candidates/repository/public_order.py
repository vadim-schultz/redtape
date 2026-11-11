"""Sort keys of the public candidate list and the order-by clauses each one builds."""

from __future__ import annotations

import enum
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from sqlalchemy import ColumnElement
from sqlalchemy.sql.expression import Subquery

from app.features.discovery.repository.candidate_completeness import completeness_order
from app.features.discovery.repository.candidate_sort import (
    CandidateSortKey,
    MentionCount,
    Ordering,
    candidate_ordering,
    directed,
    tie_break,
)
from app.shared.list_query import SortOrder


class PublicSortKey(enum.StrEnum):
    """Public sort fields: the admin keys plus completeness, confidence and the combined score (the default)."""

    COMBINED = "combined"
    COMPLETENESS = "completeness"
    MENTIONS = "mentions"
    TITLE = "title"
    CREATED_AT = "created_at"
    CONFIDENCE = "confidence"


@dataclass(frozen=True, slots=True)
class RankColumns:
    """The columns a public ordering reads: completeness, mention count, confidence, combined score and relevance.

    ``score`` is the confidence itself without a search; ``relevance`` exists only for a search.
    """

    completeness: Subquery
    mention_count: MentionCount
    confidence: ColumnElement[float]
    score: ColumnElement[float]
    relevance: ColumnElement[float] | None = None


Rank = Callable[[RankColumns, SortOrder], Ordering]


def _by_confidence(columns: RankColumns, order: SortOrder) -> Ordering:
    return (directed(columns.confidence, order), *tie_break())


def _by_completeness(columns: RankColumns, order: SortOrder) -> Ordering:
    return (*completeness_order(columns.completeness, columns.mention_count, order), *tie_break())


def _browse_order(columns: RankColumns) -> Ordering:
    """Order by confidence, then completeness, then mentions, all best first."""
    ranked = (
        columns.confidence.desc(),
        *completeness_order(columns.completeness, columns.mention_count, SortOrder.DESC),
    )
    return (*ranked, *tie_break())


def _search_order(columns: RankColumns, relevance: ColumnElement[float]) -> Ordering:
    """Order by the combined score, then relevance, then confidence, all best first."""
    return (columns.score.desc(), relevance.desc(), columns.confidence.desc(), *tie_break())


def _by_combined(columns: RankColumns, _order: SortOrder) -> Ordering:
    """Order by the combined score of a search, else as a browse, always best first."""
    if columns.relevance is None:
        return _browse_order(columns)
    return _search_order(columns, columns.relevance)


def _admin(key: CandidateSortKey) -> Rank:
    """Return the ordering of an admin sort key, which reads only the mention count."""
    return lambda columns, order: candidate_ordering(key, order, columns.mention_count)


RANKS: Mapping[PublicSortKey, Rank] = {
    PublicSortKey.COMBINED: _by_combined,
    PublicSortKey.CONFIDENCE: _by_confidence,
    PublicSortKey.COMPLETENESS: _by_completeness,
    PublicSortKey.MENTIONS: _admin(CandidateSortKey.MENTIONS),
    PublicSortKey.TITLE: _admin(CandidateSortKey.TITLE),
    PublicSortKey.CREATED_AT: _admin(CandidateSortKey.CREATED_AT),
}
