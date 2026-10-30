"""The description of a candidate: the excerpt of its best mention (D4)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import NamedTuple
from uuid import UUID

from sqlalchemy import select

from app.features.candidates.roles import role_rank_column
from app.features.discovery.repository.base import SessionRepository
from app.models.discovery import CatalogueService
from app.models.discovery import DiscoveryCandidateMention as Mention


class DescriptionRow(NamedTuple):
    """The best mention of one candidate and the title of its procedure."""

    candidate_id: UUID
    excerpt: str
    procedure_title_i18n: dict[str, str]


class DescriptionRepository(SessionRepository):
    """Pick one mention per candidate, for a page of ids only."""

    def best_descriptions(self, candidate_ids: Sequence[UUID]) -> dict[UUID, DescriptionRow]:
        """Return the best mention of each id by role, then age, then id; ids without a mention are absent."""
        if not candidate_ids:
            return {}
        stmt = (
            select(Mention.candidate_id, Mention.excerpt, CatalogueService.title_i18n)
            .join(CatalogueService, CatalogueService.id == Mention.catalogue_service_id)
            .where(Mention.candidate_id.in_(candidate_ids))
            .distinct(Mention.candidate_id)
            .order_by(Mention.candidate_id, role_rank_column(), Mention.created_at.asc(), Mention.id.asc())
        )
        rows = (DescriptionRow(*row) for row in self._session.execute(stmt).all())
        return {row.candidate_id: row for row in rows}
