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
    tie_break,
)
from app.shared.list_query import SortOrder


class PublicSortKey(enum.StrEnum):
    """Public sort fields: the admin keys plus completeness and confidence."""

    COMPLETENESS = "completeness"
    MENTIONS = "mentions"
    TITLE = "title"
    CREATED_AT = "created_at"
    CONFIDENCE = "confidence"


@dataclass(frozen=True, slots=True)
class RankColumns:
    """The columns a public ordering reads: completeness model, mention count and the card confidence."""

    completeness: Subquery
    mention_count: MentionCount
    confidence: ColumnElement[float]


Rank = Callable[[RankColumns, SortOrder], Ordering]


def _directed(column: ColumnElement, order: SortOrder) -> ColumnElement:
    return column.desc() if order is SortOrder.DESC else column.asc()


def _by_confidence(columns: RankColumns, order: SortOrder) -> Ordering:
    return (_directed(columns.confidence, order), *tie_break())


def _by_completeness(columns: RankColumns, order: SortOrder) -> Ordering:
    return (*completeness_order(columns.completeness, columns.mention_count, order), *tie_break())


def _by_default(columns: RankColumns, _order: SortOrder) -> Ordering:
    """Confidence, then completeness, then mentions, all best first."""
    ranked = (
        columns.confidence.desc(),
        *completeness_order(columns.completeness, columns.mention_count, SortOrder.DESC),
    )
    return (*ranked, *tie_break())


def _admin(key: CandidateSortKey) -> Rank:
    """Return the ordering of an admin sort key, which reads only the mention count."""
    return lambda columns, order: candidate_ordering(key, order, columns.mention_count)


RANKS: Mapping[PublicSortKey | None, Rank] = {
    None: _by_default,
    PublicSortKey.CONFIDENCE: _by_confidence,
    PublicSortKey.COMPLETENESS: _by_completeness,
    PublicSortKey.MENTIONS: _admin(CandidateSortKey.MENTIONS),
    PublicSortKey.TITLE: _admin(CandidateSortKey.TITLE),
    PublicSortKey.CREATED_AT: _admin(CandidateSortKey.CREATED_AT),
}
