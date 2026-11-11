"""Pages of candidates in the public order, and one candidate's card row."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select

from app.features.candidates.repository.cards import CardRelations, CardRow
from app.features.candidates.repository.public_filter import PublicCandidateFilter
from app.features.discovery.repository.base import SessionRepository
from app.features.discovery.repository.task_listing import Page
from app.models.discovery import DiscoveryDocumentCandidate as Candidate


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
