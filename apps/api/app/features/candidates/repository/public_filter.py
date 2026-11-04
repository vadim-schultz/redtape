"""Filter options and ordering of the public candidate list."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import ColumnElement, false, or_
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
    groups: tuple[str, ...] = ()
    category_codes: tuple[str, ...] = ()
    category_domain_codes: tuple[str, ...] = ()
    category_situation_codes: tuple[str, ...] = ()
    q: str | None = None
    sort_by: PublicSortKey | None = None
    sort_order: SortOrder = SortOrder.DESC

    @property
    def selected(self) -> Selected:
        """The legacy-axis score rows needed to evaluate canonical and legacy filters."""
        pairs = (
            (TagAxis.DOMAIN, (*self.domains, *self.category_domain_codes)),
            (TagAxis.SITUATION, (*self.situations, *self.category_situation_codes)),
        )
        return tuple((axis, tuple(dict.fromkeys(codes))) for axis, codes in pairs if codes)

    def conditions(self, completeness: Subquery, best: Subquery) -> list[ColumnElement[bool]]:
        """Return the where-clauses of the filters that are set: a code matches by presence in ``best``."""
        conditions = [
            *when(self.complete, lambda value: completeness.c.complete.is_(value)),
            *when(self.q, title_matches),
        ]
        category_axes = (
            (TagAxis.DOMAIN, self.category_domain_codes),
            (TagAxis.SITUATION, self.category_situation_codes),
        )
        if any(codes for _, codes in category_axes):
            conditions.append(or_(*(best.c[axis_best(axis)].is_not(None) for axis, codes in category_axes if codes)))
        elif self.category_codes:
            conditions.append(false())
        conditions.extend(
            best.c[axis_best(axis)].is_not(None)
            for axis, codes in ((TagAxis.DOMAIN, self.domains), (TagAxis.SITUATION, self.situations))
            if codes
        )
        return conditions

    def ordering(
        self, completeness: Subquery, mention_count: MentionCount, confidence: ColumnElement[float]
    ) -> Ordering:
        """Return the order-by clauses of the chosen sort, always ending in the deterministic tie-break."""
        return RANKS[self.sort_by](RankColumns(completeness, mention_count, confidence), self.sort_order)
