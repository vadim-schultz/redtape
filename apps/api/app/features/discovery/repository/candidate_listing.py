"""Candidate listings for the admin API."""

from __future__ import annotations

from typing import NamedTuple
from uuid import UUID

from sqlalchemy import func, select

from app.features.discovery.repository.base import SessionRepository
from app.features.discovery.repository.candidate_filter import CandidateFilter
from app.features.discovery.repository.candidate_relations import mention_count_of, mention_stats, with_stats
from app.features.discovery.repository.task_listing import Page
from app.models.discovery import (
    CatalogueService,
    DiscoveryArtifact,
    DiscoveryCandidateMention,
    DiscoveryDocumentCandidate,
)
from app.models.jurisdiction import Jurisdiction

__all__ = [
    "CandidateListRow",
    "CandidateListingRepository",
    "CandidateMentionRow",
    "mention_count_of",
    "mention_stats",
    "with_stats",
]


class CandidateListRow(NamedTuple):
    """One listed candidate with its mention statistics and jurisdiction names."""

    candidate: DiscoveryDocumentCandidate
    mention_count: int
    roles: list[str]
    jurisdiction_name_i18n: dict[str, str]


class CandidateMentionRow(NamedTuple):
    """One mention with the procedure it was found in and the artifact it cites, if any."""

    mention: DiscoveryCandidateMention
    procedure: CatalogueService
    artifact: DiscoveryArtifact | None


class CandidateListingRepository(SessionRepository):
    """List candidates with their mention counts and mentions with their procedures."""

    def count_candidates(self, candidate_filter: CandidateFilter) -> int:
        """Count the candidates that match ``candidate_filter``."""
        relations = candidate_filter.relations()
        stmt = relations.join(select(func.count()).select_from(DiscoveryDocumentCandidate))
        return int(self._session.scalar(stmt.where(*candidate_filter.conditions(relations))) or 0)

    def list_candidates_page(self, page: Page, candidate_filter: CandidateFilter) -> list[CandidateListRow]:
        """Return one page of matching candidates in the filter's order."""
        relations = candidate_filter.relations()
        columns = select(
            DiscoveryDocumentCandidate, relations.mention_count, relations.stats.c.roles, Jurisdiction.name_i18n
        )
        stmt = relations.join(columns).join(Jurisdiction, Jurisdiction.id == DiscoveryDocumentCandidate.jurisdiction_id)
        stmt = stmt.where(*candidate_filter.conditions(relations)).order_by(*candidate_filter.ordering(relations))
        rows = self._session.execute(stmt.offset(page.offset).limit(page.limit)).all()
        return [CandidateListRow(row[0], row[1], sorted(row[2] or []), row[3]) for row in rows]

    def get_candidate(self, candidate_id: UUID) -> DiscoveryDocumentCandidate | None:
        """Return the candidate with ``candidate_id``, if any."""
        return self._session.get(DiscoveryDocumentCandidate, candidate_id)

    def list_candidate_mentions(self, candidate_id: UUID) -> list[CandidateMentionRow]:
        """Return the mentions of one candidate with their procedures and artifacts, oldest first."""
        stmt = (
            select(DiscoveryCandidateMention, CatalogueService, DiscoveryArtifact)
            .join(CatalogueService, DiscoveryCandidateMention.catalogue_service_id == CatalogueService.id)
            .outerjoin(DiscoveryArtifact, DiscoveryCandidateMention.artifact_id == DiscoveryArtifact.id)
            .where(DiscoveryCandidateMention.candidate_id == candidate_id)
            .order_by(DiscoveryCandidateMention.created_at.asc(), DiscoveryCandidateMention.id.asc())
        )
        return [CandidateMentionRow(*row) for row in self._session.execute(stmt).all()]
