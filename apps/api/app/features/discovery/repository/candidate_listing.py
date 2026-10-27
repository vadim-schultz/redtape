"""Candidate listings for the admin API."""

from __future__ import annotations

from typing import NamedTuple
from uuid import UUID

from sqlalchemy import ColumnElement, Select, String, cast, distinct, func, select
from sqlalchemy.sql.expression import Subquery

from app.features.discovery.repository.base import SessionRepository
from app.features.discovery.repository.candidate_filter import CandidateFilter
from app.features.discovery.repository.task_listing import Page
from app.models.discovery import (
    CatalogueService,
    DiscoveryArtifact,
    DiscoveryCandidateMention,
    DiscoveryDocumentCandidate,
)
from app.models.jurisdiction import Jurisdiction


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


def _mention_stats() -> Subquery:
    role = cast(DiscoveryCandidateMention.role, String)
    return (
        select(
            DiscoveryCandidateMention.candidate_id,
            func.count(DiscoveryCandidateMention.id).label("mention_count"),
            func.array_agg(distinct(role)).label("roles"),
        )
        .group_by(DiscoveryCandidateMention.candidate_id)
        .subquery()
    )


def _count_of(stats: Subquery) -> ColumnElement[int]:
    return func.coalesce(stats.c.mention_count, 0)


def _with_stats(stmt: Select, stats: Subquery) -> Select:
    return stmt.outerjoin(stats, stats.c.candidate_id == DiscoveryDocumentCandidate.id)


class CandidateListingRepository(SessionRepository):
    """List candidates with their mention counts and mentions with their procedures."""

    def count_candidates(self, candidate_filter: CandidateFilter) -> int:
        """Count the candidates that match ``candidate_filter``."""
        stats = _mention_stats()
        stmt = _with_stats(select(func.count()).select_from(DiscoveryDocumentCandidate), stats)
        return int(self._session.scalar(stmt.where(*candidate_filter.conditions(_count_of(stats)))) or 0)

    def list_candidates_page(self, page: Page, candidate_filter: CandidateFilter) -> list[CandidateListRow]:
        """Return one page of matching candidates in the filter's order."""
        stats = _mention_stats()
        count = _count_of(stats)
        columns = select(DiscoveryDocumentCandidate, count, stats.c.roles, Jurisdiction.name_i18n)
        stmt = _with_stats(columns, stats).join(
            Jurisdiction, Jurisdiction.id == DiscoveryDocumentCandidate.jurisdiction_id
        )
        stmt = stmt.where(*candidate_filter.conditions(count)).order_by(*candidate_filter.ordering(count))
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
