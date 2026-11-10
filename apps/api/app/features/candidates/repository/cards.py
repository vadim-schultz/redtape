"""Pages of candidates joined to the completeness read model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple
from uuid import UUID

from sqlalchemy import ColumnElement, Select, func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import Subquery

from app.features.candidates.repository.public_filter import PublicCandidateFilter
from app.features.candidates.repository.public_order import RankColumns
from app.features.candidates.repository.public_scores import best_scores
from app.features.discovery.repository.base import SessionRepository
from app.features.discovery.repository.candidate_completeness import completeness_subquery
from app.features.discovery.repository.candidate_listing import mention_count_of, mention_stats, with_stats
from app.features.discovery.repository.candidate_tag_scores import tag_scores_subquery
from app.features.discovery.repository.task_listing import Page
from app.features.search.retrieval import Retrieval, fused_relation
from app.models.discovery import DiscoveryDocumentCandidate as Candidate


class CardRow(NamedTuple):
    """One listed candidate, its mention count and its card confidence; a search adds its relevance and cosine."""

    candidate: Candidate
    mention_count: int
    confidence: float
    relevance: float | None = None
    cosine: float | None = None


@dataclass(frozen=True, slots=True)
class FusedSearch:
    """A search's retrieval and the fused pool ``(candidate_id, rrf, cos, relevance)`` its legs produced."""

    retrieval: Retrieval
    pool: Subquery


@dataclass(frozen=True, slots=True)
class CardRelations:
    """The relations a card query reads: statistics, completeness, best scores and, for a search, the fused pool."""

    stats: Subquery
    completeness: Subquery
    best: Subquery
    search: FusedSearch | None = None

    @classmethod
    def build(cls, card_filter: PublicCandidateFilter) -> CardRelations:
        """Build the relations; the best scores are those among ``card_filter``'s selected categories.

        A search's legs are scoped by the same completeness and category filters as the list itself.
        """
        completeness = completeness_subquery()
        best = best_scores(tag_scores_subquery(), card_filter.category_codes)
        stats = mention_stats()
        if card_filter.search is None:
            return cls(stats, completeness, best)
        pool = fused_relation(card_filter.search, card_filter.scope(completeness, best))
        return cls(stats, completeness, best, FusedSearch(card_filter.search, pool))

    def prepare(self, session: Session) -> None:
        """Apply the session settings a search needs; a browse needs none."""
        if self.search is not None:
            self.search.retrieval.prepare(session)

    @property
    def rank_columns(self) -> RankColumns:
        """The columns an ordering reads, the relevance of the fused pool among them."""
        relevance = None if self.search is None else self.search.pool.c.relevance
        return RankColumns(self.completeness, self.mention_count, self.confidence, relevance)

    @property
    def mention_count(self) -> ColumnElement[int]:
        """The mention count column, ``0`` without a mention."""
        return mention_count_of(self.stats)

    @property
    def confidence(self) -> ColumnElement[float]:
        """The card confidence, ``0`` without a score: the labelled column a page selects and orders by."""
        return func.coalesce(self.best.c.best, 0.0).label("confidence")

    def conditions(self, card_filter: PublicCandidateFilter) -> list[ColumnElement[bool]]:
        """Return the where-clauses of ``card_filter`` over these relations."""
        return card_filter.conditions(self.completeness, self.best)

    def cards(self) -> Select:
        """Select candidates with their mention count, confidence and search columns, joined to all relations."""
        return self.join(select(Candidate, self.mention_count, self.confidence, *self._search_columns()))

    def join(self, stmt: Select) -> Select:
        """Join all relations to a select over candidates; a candidate without a best score keeps its row.

        A search keeps only the candidates of its fused pool, so the list and its count read the same rows.
        """
        joined = with_stats(stmt, self.stats)
        joined = joined.join(self.completeness, self.completeness.c.candidate_id == Candidate.id)
        joined = joined.outerjoin(self.best, self.best.c.candidate_id == Candidate.id)
        if self.search is None:
            return joined
        return joined.join(self.search.pool, self.search.pool.c.candidate_id == Candidate.id)

    def _search_columns(self) -> list[ColumnElement[float]]:
        return [] if self.search is None else [self.search.pool.c.relevance, self.search.pool.c.cos]


class CardRepository(SessionRepository):
    """Page through candidates with their mention counts in the public order."""

    def count_cards(self, card_filter: PublicCandidateFilter) -> int:
        """Count the candidates that match ``card_filter``."""
        relations = CardRelations.build(card_filter)
        relations.prepare(self._session)
        stmt = relations.join(select(func.count()).select_from(Candidate))
        return int(self._session.scalar(stmt.where(*relations.conditions(card_filter))) or 0)

    def list_card_rows(self, card_filter: PublicCandidateFilter, page: Page) -> list[CardRow]:
        """Return one page of matching candidates in the filter's order, each with the confidence it is ordered by."""
        relations = CardRelations.build(card_filter)
        relations.prepare(self._session)
        stmt = relations.cards().where(*relations.conditions(card_filter))
        stmt = stmt.order_by(*card_filter.ordering(relations.rank_columns))
        return [CardRow(*row) for row in self._session.execute(stmt.offset(page.offset).limit(page.limit)).all()]

    def get_card_row(self, candidate_id: UUID) -> CardRow | None:
        """Return the candidate with its mention count and its confidence over all tags, or ``None`` when unknown."""
        stmt = CardRelations.build(PublicCandidateFilter()).cards().where(Candidate.id == candidate_id)
        row = self._session.execute(stmt).first()
        return None if row is None else CardRow(*row)
