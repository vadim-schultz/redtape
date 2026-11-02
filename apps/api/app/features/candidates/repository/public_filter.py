"""Filter options and ordering of the public candidate list."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import ColumnElement
from sqlalchemy.sql.expression import Subquery

from app.features.candidates.repository.public_order import RANKS, PublicSortKey, RankColumns
from app.features.candidates.repository.public_scores import Selected, axis_best
from app.features.discovery.repository.candidate_filter import title_matches, when
from app.features.discovery.repository.candidate_sort import MentionCount, Ordering
from app.features.discovery.tags import TagAxis
from app.shared.list_query import SortOrder

__all__ = ["PublicCandidateFilter", "PublicSortKey"]


@dataclass(frozen=True, slots=True)
class PublicCandidateFilter:
    """Optional narrowing and ordering of one public listing; without ``sort_by`` it is the ranked list."""

    complete: bool | None = None
    domains: tuple[str, ...] = ()
    situations: tuple[str, ...] = ()
    q: str | None = None
    sort_by: PublicSortKey | None = None
    sort_order: SortOrder = SortOrder.DESC

    @property
    def selected(self) -> Selected:
        """The axes that have codes selected, each with its codes."""
        pairs = ((TagAxis.DOMAIN, self.domains), (TagAxis.SITUATION, self.situations))
        return tuple((axis, codes) for axis, codes in pairs if codes)

    def conditions(self, completeness: Subquery, best: Subquery) -> list[ColumnElement[bool]]:
        """Return the where-clauses of the filters that are set: a code matches by presence in ``best``."""
        return [
            *when(self.complete, lambda value: completeness.c.complete.is_(value)),
            *(best.c[axis_best(axis)].is_not(None) for axis, _ in self.selected),
            *when(self.q, title_matches),
        ]

    def ordering(
        self, completeness: Subquery, mention_count: MentionCount, confidence: ColumnElement[float]
    ) -> Ordering:
        """Return the order-by clauses of the chosen sort, always ending in the deterministic tie-break."""
        return RANKS[self.sort_by](RankColumns(completeness, mention_count, confidence), self.sort_order)
