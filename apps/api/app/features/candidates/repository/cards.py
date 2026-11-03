"""Pages of candidates joined to the completeness read model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple
from uuid import UUID

from sqlalchemy import ColumnElement, Select, func, select
from sqlalchemy.sql.expression import Subquery

from app.features.candidates.repository.public_filter import PublicCandidateFilter
from app.features.candidates.repository.public_scores import best_scores
from app.features.discovery.repository.base import SessionRepository
from app.features.discovery.repository.candidate_completeness import completeness_subquery
from app.features.discovery.repository.candidate_listing import mention_count_of, mention_stats, with_stats
from app.features.discovery.repository.candidate_tag_scores import tag_scores_subquery
from app.features.discovery.repository.task_listing import Page
from app.models.discovery import DiscoveryDocumentCandidate as Candidate


class CardRow(NamedTuple):
    """One listed candidate, its mention count and its card confidence."""

    candidate: Candidate
    mention_count: int
    confidence: float


@dataclass(frozen=True, slots=True)
class CardRelations:
    """The relations a card query reads: mention statistics, the completeness read model and the best scores."""

    stats: Subquery
    completeness: Subquery
    best: Subquery

    @classmethod
    def build(cls, card_filter: PublicCandidateFilter) -> CardRelations:
        """Build the relations; the best scores are those among ``card_filter``'s selected codes."""
        return cls(mention_stats(), completeness_subquery(), best_scores(tag_scores_subquery(), card_filter.selected))

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
        """Select candidates with their mention count and confidence, joined to all relations."""
        return self.join(select(Candidate, self.mention_count, self.confidence))

    def join(self, stmt: Select) -> Select:
        """Join all relations to a select over candidates; a candidate without a best score keeps its row."""
        joined = with_stats(stmt, self.stats)
        joined = joined.join(self.completeness, self.completeness.c.candidate_id == Candidate.id)
        return joined.outerjoin(self.best, self.best.c.candidate_id == Candidate.id)


class CardRepository(SessionRepository):
    """Page through candidates with their mention counts in the public order."""

    def count_cards(self, card_filter: PublicCandidateFilter) -> int:
        """Count the candidates that match ``card_filter``."""
        relations = CardRelations.build(card_filter)
        stmt = relations.join(select(func.count()).select_from(Candidate))
        return int(self._session.scalar(stmt.where(*relations.conditions(card_filter))) or 0)

    def list_card_rows(self, card_filter: PublicCandidateFilter, page: Page) -> list[CardRow]:
        """Return one page of matching candidates in the filter's order, each with the confidence it is ordered by."""
        relations = CardRelations.build(card_filter)
        stmt = relations.cards().where(*relations.conditions(card_filter))
        stmt = stmt.order_by(
            *card_filter.ordering(relations.completeness, relations.mention_count, relations.confidence)
        )
        return [CardRow(*row) for row in self._session.execute(stmt.offset(page.offset).limit(page.limit)).all()]

    def get_card_row(self, candidate_id: UUID) -> CardRow | None:
        """Return the candidate with its mention count and its confidence over all tags, or ``None`` when unknown."""
        stmt = CardRelations.build(PublicCandidateFilter()).cards().where(Candidate.id == candidate_id)
        row = self._session.execute(stmt).first()
        return None if row is None else CardRow(*row)
