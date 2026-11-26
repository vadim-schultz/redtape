"""Reads of the German source of a translation: the unit of each candidate and the confidence that ranks it."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Final
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.features.candidates.card_builder import DESCRIPTION_MAX_LENGTH
from app.features.candidates.repository.descriptions import DescriptionRepository, DescriptionRow
from app.features.candidates.repository.tag_scores import TagScoreRepository
from app.features.discovery.repository.base import SessionRepository
from app.features.translation.unit import TranslationUnit, german_title
from app.models.discovery import DiscoveryDocumentCandidate as Candidate
from app.models.fair_selection_state import FairSelectionState

CANDIDATE_PIPELINE: Final = "translation"
"""The fair_selection_state pipeline of candidates, the entities of the translation queue."""
PAGE_PIPELINE: Final = "snapshot_translation"
"""The fair_selection_state pipeline of procedure pages, the entities of the snapshot translation queue."""


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


def get_phase_for_candidate(session: Session, candidate_id: UUID) -> int:
    """Read phase for a candidate; default to phase 1 if not found."""
    state = (
        session.query(FairSelectionState)
        .filter(
            FairSelectionState.pipeline == CANDIDATE_PIPELINE,
            FairSelectionState.entity_id == candidate_id,
        )
        .first()
    )
    return state.phase if state else 1


def get_phases_for_candidates(session: Session, candidate_ids: Sequence[UUID]) -> dict[UUID, int]:
    """Read phases for multiple candidates; fill in defaults for missing entries."""
    if not candidate_ids:
        return {}

    states = (
        session.query(FairSelectionState)
        .filter(
            FairSelectionState.pipeline == CANDIDATE_PIPELINE,
            FairSelectionState.entity_id.in_(candidate_ids),
        )
        .all()
    )

    result = {s.entity_id: s.phase for s in states}

    # Fill in defaults for missing entries
    for cid in candidate_ids:
        if cid not in result:
            result[cid] = 1

    return result


def get_phase_for_page(session: Session, catalogue_service_id: UUID) -> int:
    """Read phase for a page; default to phase 1 if not found."""
    state = (
        session.query(FairSelectionState)
        .filter(
            FairSelectionState.pipeline == PAGE_PIPELINE,
            FairSelectionState.entity_id == catalogue_service_id,
        )
        .first()
    )
    return state.phase if state else 1


def get_phases_for_pages(session: Session, page_ids: Iterable[UUID]) -> dict[UUID, int]:
    """Read phases for multiple pages in one batch query; fill in defaults for missing entries."""
    page_ids_list = list(page_ids)
    if not page_ids_list:
        return {}

    states = (
        session.query(FairSelectionState)
        .filter(
            FairSelectionState.pipeline == PAGE_PIPELINE,
            FairSelectionState.entity_id.in_(page_ids_list),
        )
        .all()
    )

    result = {s.entity_id: s.phase for s in states}

    # Fill in defaults for missing entries
    for page_id in page_ids_list:
        if page_id not in result:
            result[page_id] = 1

    return result
