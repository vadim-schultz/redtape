"""Filter options and ordering of the public candidate list."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import ColumnElement
from sqlalchemy.sql.expression import Subquery

from app.features.candidates.repository.public_order import RANKS, PublicSortKey, RankColumns
from app.features.discovery.repository.candidate_filter import title_matches, when
from app.features.discovery.repository.candidate_sort import MentionCount, Ordering
from app.shared.list_query import SortOrder

__all__ = ["PublicCandidateFilter", "PublicSortKey"]


@dataclass(frozen=True, slots=True)
class PublicCandidateFilter:
    """Optional narrowing and ordering of one public listing; without ``sort_by`` it is the ranked list.

    ``category_codes`` are the selected codes already expanded to their descendants by the service.
    """

    complete: bool | None = None
    category_codes: tuple[str, ...] = ()
    q: str | None = None
    sort_by: PublicSortKey | None = None
    sort_order: SortOrder = SortOrder.DESC

    def conditions(self, completeness: Subquery, best: Subquery) -> list[ColumnElement[bool]]:
        """Return the where-clauses of the filters that are set; a category matches by presence in ``best``."""
        conditions = [
            *when(self.complete, lambda value: completeness.c.complete.is_(value)),
            *when(self.q, title_matches),
        ]
        if self.category_codes:
            conditions.append(best.c.best.is_not(None))
        return conditions

    def ordering(
        self, completeness: Subquery, mention_count: MentionCount, confidence: ColumnElement[float]
    ) -> Ordering:
        """Return the order-by clauses of the chosen sort, always ending in the deterministic tie-break."""
        return RANKS[self.sort_by](RankColumns(completeness, mention_count, confidence), self.sort_order)
