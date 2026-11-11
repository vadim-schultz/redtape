"""Pages of candidates joined to the completeness read model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple

from sqlalchemy import ColumnElement, Select, func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import Subquery

from app.features.candidates.repository.card_search import CardSearch, FusedSearch, NoSearch
from app.features.candidates.repository.public_filter import PublicCandidateFilter
from app.features.candidates.repository.public_order import RankColumns
from app.features.candidates.repository.public_scores import best_scores
from app.features.discovery.repository.candidate_completeness import completeness_subquery
from app.features.discovery.repository.candidate_listing import mention_count_of, mention_stats, with_stats
from app.features.discovery.repository.candidate_tag_scores import tag_scores_subquery
from app.features.search.retrieval import fused_relation
from app.models.discovery import DiscoveryDocumentCandidate as Candidate


class CardRow(NamedTuple):
    """One listed candidate, its mention count, card confidence and ranking score; a search adds relevance and cosine."""

    candidate: Candidate
    mention_count: int
    confidence: float
    score: float
    relevance: float | None = None
    cosine: float | None = None


@dataclass(frozen=True, slots=True)
class CardRelations:
    """The relations a card query reads: statistics, completeness, best scores and, for a search, the fused pool."""

    stats: Subquery
    completeness: Subquery
    best: Subquery
    search: CardSearch = NoSearch()

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
        self.search.prepare(session)

    @property
    def rank_columns(self) -> RankColumns:
        """The columns an ordering reads, the relevance of the fused pool among them."""
        return RankColumns(self.completeness, self.mention_count, self.confidence, self.score, self.search.relevance)

    @property
    def mention_count(self) -> ColumnElement[int]:
        """The mention count column, ``0`` without a mention."""
        return mention_count_of(self.stats)

    @property
    def confidence(self) -> ColumnElement[float]:
        """The card confidence, ``0`` without a score: the labelled column a page selects and orders by."""
        return self._confidence.label("confidence")

    @property
    def score(self) -> ColumnElement[float]:
        """The ranking score: the combined score of a search, else the confidence; the labelled column a page selects."""
        return self.search.score(self._confidence).label("score")

    @property
    def _confidence(self) -> ColumnElement[float]:
        return func.coalesce(self.best.c.best, 0.0)

    def conditions(self, card_filter: PublicCandidateFilter) -> list[ColumnElement[bool]]:
        """Return the where-clauses of ``card_filter`` over these relations."""
        return card_filter.conditions(self.completeness, self.best)

    def cards(self) -> Select:
        """Select candidates with their mention count, confidence, score and search columns, joined to all relations."""
        return self.join(select(Candidate, self.mention_count, self.confidence, self.score, *self.search.columns))

    def join(self, stmt: Select) -> Select:
        """Join all relations to a select over candidates; a candidate without a best score keeps its row.

        A search keeps only the candidates of its fused pool, so the list and its count read the same rows.
        """
        joined = with_stats(stmt, self.stats)
        joined = joined.join(self.completeness, self.completeness.c.candidate_id == Candidate.id)
        joined = joined.outerjoin(self.best, self.best.c.candidate_id == Candidate.id)
        return self.search.join(joined)
