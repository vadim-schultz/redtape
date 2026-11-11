"""Reads of the German source of a translation: the unit of each candidate and the confidence that ranks it."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select

from app.features.candidates.card_builder import DESCRIPTION_MAX_LENGTH
from app.features.candidates.repository.descriptions import DescriptionRepository, DescriptionRow
from app.features.candidates.repository.tag_scores import TagScoreRepository
from app.features.discovery.repository.base import SessionRepository
from app.features.translation.unit import TranslationUnit, german_title
from app.models.discovery import DiscoveryDocumentCandidate as Candidate


class SourceRepository(SessionRepository):
    """Read the German unit and the confidence of candidates."""

    def units_for(self, candidate_ids: Sequence[UUID]) -> dict[UUID, TranslationUnit]:
        """Return the unit of every candidate that has a German title; the others are absent.

        The description is the excerpt of the best mention, cut as the card cuts it, and empty without a mention.
        """
        if not candidate_ids:
            return {}
        stmt = select(Candidate.id, Candidate.title_i18n).where(Candidate.id.in_(candidate_ids))
        titles = dict(self._session.execute(stmt).tuples().all())
        descriptions = DescriptionRepository(self._session).best_descriptions(candidate_ids)
        return {
            candidate_id: TranslationUnit(title, _description(descriptions.get(candidate_id)))
            for candidate_id, title_i18n in titles.items()
            if (title := german_title(title_i18n))
        }

    def confidences_for(self, candidate_ids: Sequence[UUID]) -> dict[UUID, float]:
        """Return the confidence of each candidate as its card shows it: its best category score, ``0.0`` without one."""
        scored = TagScoreRepository(self._session).tag_scores_for(candidate_ids)
        return {
            candidate_id: scored[candidate_id][0].score if candidate_id in scored else 0.0
            for candidate_id in candidate_ids
        }


def _description(row: DescriptionRow | None) -> str:
    """Return the excerpt of ``row`` cut as the card cuts it, so the unit is the text the card shows."""
    return "" if row is None else row.excerpt[:DESCRIPTION_MAX_LENGTH]
