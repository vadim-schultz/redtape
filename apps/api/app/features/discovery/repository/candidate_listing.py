"""Candidate listings for the admin API."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, func, select

from app.features.discovery.repository.base import SessionRepository
from app.features.discovery.repository.task_listing import Page
from app.models.discovery import (
    CatalogueService,
    DiscoveryCandidateMention,
    DiscoveryCandidateStatus,
    DiscoveryDocumentCandidate,
)

CANDIDATE_ORDER = (DiscoveryDocumentCandidate.created_at.desc(), DiscoveryDocumentCandidate.key.asc())


def _filtered(stmt: Select, status: DiscoveryCandidateStatus | None) -> Select:
    if status is None:
        return stmt
    return stmt.where(DiscoveryDocumentCandidate.status == status)


def _with_mention_counts() -> Select:
    return (
        select(DiscoveryDocumentCandidate, func.count(DiscoveryCandidateMention.id))
        .outerjoin(DiscoveryCandidateMention, DiscoveryCandidateMention.candidate_id == DiscoveryDocumentCandidate.id)
        .group_by(DiscoveryDocumentCandidate.id)
        .order_by(*CANDIDATE_ORDER)
    )


class CandidateListingRepository(SessionRepository):
    """List candidates with their mention counts and mentions with their procedures."""

    def count_candidates(self, *, status: DiscoveryCandidateStatus | None = None) -> int:
        """Count candidates, optionally filtered by ``status``."""
        stmt = _filtered(select(func.count()).select_from(DiscoveryDocumentCandidate), status)
        return int(self._session.scalar(stmt) or 0)

    def list_candidates_page(
        self, page: Page, *, status: DiscoveryCandidateStatus | None = None
    ) -> list[tuple[DiscoveryDocumentCandidate, int]]:
        """Return one page of candidates with their mention counts, newest first."""
        stmt = _filtered(_with_mention_counts(), status).offset(page.offset).limit(page.limit)
        return list(self._session.execute(stmt).tuples().all())

    def get_candidate(self, candidate_id: UUID) -> DiscoveryDocumentCandidate | None:
        """Return the candidate with ``candidate_id``, if any."""
        return self._session.get(DiscoveryDocumentCandidate, candidate_id)

    def list_candidate_mentions(self, candidate_id: UUID) -> list[tuple[DiscoveryCandidateMention, CatalogueService]]:
        """Return the mentions of one candidate with their procedures, oldest first."""
        stmt = (
            select(DiscoveryCandidateMention, CatalogueService)
            .join(CatalogueService, DiscoveryCandidateMention.catalogue_service_id == CatalogueService.id)
            .where(DiscoveryCandidateMention.candidate_id == candidate_id)
            .order_by(DiscoveryCandidateMention.created_at.asc(), DiscoveryCandidateMention.id.asc())
        )
        return list(self._session.execute(stmt).tuples().all())
