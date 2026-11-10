"""Filter options and ordering of the public candidate list."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import ColumnElement, Select, select
from sqlalchemy.sql.expression import Subquery

from app.features.candidates.repository.public_order import RANKS, PublicSortKey, RankColumns, by_relevance
from app.features.discovery.repository.candidate_filter import title_matches, when
from app.features.discovery.repository.candidate_sort import Ordering
from app.features.search.retrieval import Retrieval
from app.models.discovery import DiscoveryDocumentCandidate as Candidate
from app.shared.list_query import SortOrder

__all__ = ["PublicCandidateFilter", "PublicSortKey"]


@dataclass(frozen=True, slots=True)
class PublicCandidateFilter:
    """Optional narrowing and ordering of one public listing; without ``sort_by`` it is the ranked list.

    ``category_codes`` are the selected codes already expanded to their descendants by the service. ``q`` is the
    legacy title match (hybrid search off); ``search`` is the retrieval the service chose for a real query and
    replaces it.
    """

    complete: bool | None = None
    category_codes: tuple[str, ...] = ()
    q: str | None = None
    search: Retrieval | None = None
    sort_by: PublicSortKey | None = None
    sort_order: SortOrder = SortOrder.DESC

    def narrowing(self, completeness: Subquery, best: Subquery) -> list[ColumnElement[bool]]:
        """Return the where-clauses of the completeness and category filters; a category matches by presence in ``best``."""
        conditions = [*when(self.complete, lambda value: completeness.c.complete.is_(value))]
        if self.category_codes:
            conditions.append(best.c.best.is_not(None))
        return conditions

    def conditions(self, completeness: Subquery, best: Subquery) -> list[ColumnElement[bool]]:
        """Return the where-clauses of the filters that are set, the legacy title match included."""
        return [*self.narrowing(completeness, best), *when(self.q, title_matches)]

    def scope(self, completeness: Subquery, best: Subquery) -> Select | None:
        """Return the ids a search leg may return, so both legs apply the same filters; ``None`` without filters."""
        conditions = self.narrowing(completeness, best)
        if not conditions:
            return None
        ids = select(Candidate.id).join(completeness, completeness.c.candidate_id == Candidate.id)
        allowed = ids.outerjoin(best, best.c.candidate_id == Candidate.id).where(*conditions).cte("search_scope")
        return select(allowed.c.id)

    def ordering(self, columns: RankColumns) -> Ordering:
        """Return the order-by clauses of the chosen sort, always ending in the deterministic tie-break.

        A search ranks by relevance unless the client chose a sort.
        """
        if self.search is not None and self.sort_by is None:
            return by_relevance(columns, self.sort_order)
        return RANKS[self.sort_by](columns, self.sort_order)
