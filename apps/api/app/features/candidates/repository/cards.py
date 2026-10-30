"""Pages of candidates joined to the completeness read model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple
from uuid import UUID

from sqlalchemy import ColumnElement, Select, func, select
from sqlalchemy.sql.expression import Subquery

from app.config import settings
from app.features.candidates.repository.public_filter import PublicCandidateFilter
from app.features.discovery.repository.base import SessionRepository
from app.features.discovery.repository.candidate_completeness import TagThresholds, completeness_subquery
from app.features.discovery.repository.candidate_listing import mention_count_of, mention_stats, with_stats
from app.features.discovery.repository.task_listing import Page
from app.models.discovery import DiscoveryDocumentCandidate as Candidate


class CardRow(NamedTuple):
    """One listed candidate and its mention count."""

    candidate: Candidate
    mention_count: int


@dataclass(frozen=True, slots=True)
class CardRelations:
    """The relations a card query joins: mention statistics and the completeness read model."""

    stats: Subquery
    completeness: Subquery

    @classmethod
    def build(cls) -> CardRelations:
        """Build both relations with the settings thresholds."""
        return cls(mention_stats(), completeness_subquery(TagThresholds.from_settings(settings)))

    @property
    def mention_count(self) -> ColumnElement[int]:
        """The mention count column, ``0`` without a mention."""
        return mention_count_of(self.stats)

    def join(self, stmt: Select) -> Select:
        """Join both relations to a select over candidates."""
        joined = with_stats(stmt, self.stats)
        return joined.join(self.completeness, self.completeness.c.candidate_id == Candidate.id)


class CardRepository(SessionRepository):
    """Page through candidates with their mention counts in the public order."""

    def count_cards(self, card_filter: PublicCandidateFilter) -> int:
        """Count the candidates that match ``card_filter``."""
        relations = CardRelations.build()
        stmt = relations.join(select(func.count()).select_from(Candidate))
        return int(self._session.scalar(stmt.where(*card_filter.conditions(relations.completeness))) or 0)

    def list_card_rows(self, card_filter: PublicCandidateFilter, page: Page) -> list[CardRow]:
        """Return one page of matching candidates in the filter's order."""
        relations = CardRelations.build()
        stmt = relations.join(select(Candidate, relations.mention_count))
        stmt = stmt.where(*card_filter.conditions(relations.completeness))
        stmt = stmt.order_by(*card_filter.ordering(relations.completeness, relations.mention_count))
        return [CardRow(*row) for row in self._session.execute(stmt.offset(page.offset).limit(page.limit)).all()]

    def get_card_row(self, candidate_id: UUID) -> CardRow | None:
        """Return the candidate with its mention count, or ``None`` when it does not exist."""
        relations = CardRelations.build()
        stmt = relations.join(select(Candidate, relations.mention_count)).where(Candidate.id == candidate_id)
        row = self._session.execute(stmt).first()
        return None if row is None else CardRow(*row)
