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
    """The best mention of one candidate: its excerpt, its procedure's title and the procedure's page and URL.

    ``source_url`` is the procedure's portal URL as stored, so it may be missing or not a web link.
    """

    candidate_id: UUID
    catalogue_service_id: UUID
    excerpt: str
    procedure_title_i18n: dict[str, str]
    source_url: str | None


class DescriptionRepository(SessionRepository):
    """Pick one mention per candidate, for a page of ids only."""

    def best_descriptions(self, candidate_ids: Sequence[UUID]) -> dict[UUID, DescriptionRow]:
        """Return the best mention of each id by role, then age, then id; ids without a mention are absent."""
        if not candidate_ids:
            return {}
        stmt = (
            select(
                Mention.candidate_id,
                Mention.catalogue_service_id,
                Mention.excerpt,
                CatalogueService.title_i18n,
                CatalogueService.portal_url,
            )
            .join(CatalogueService, CatalogueService.id == Mention.catalogue_service_id)
            .where(Mention.candidate_id.in_(candidate_ids))
            .distinct(Mention.candidate_id)
            .order_by(Mention.candidate_id, role_rank_column(), Mention.created_at.asc(), Mention.id.asc())
        )
        rows = (DescriptionRow(*row) for row in self._session.execute(stmt).all())
        return {row.candidate_id: row for row in rows}
