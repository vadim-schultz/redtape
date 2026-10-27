"""Paged artifact listings for the machine and admin APIs."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import ColumnElement, Select, func, or_, select

from app.features.discovery.repository.base import SessionRepository
from app.features.discovery.repository.task_listing import Page
from app.models.discovery import DiscoveryArtifact, DiscoveryArtifactKind, DiscoveryCandidateMention

_URL_HOST = r"^[a-zA-Z][a-zA-Z0-9+.-]*://([^/?#:]+)"


@dataclass(frozen=True, slots=True)
class ArtifactFilter:
    """Optional catalogue row, kind and source host an artifact listing is narrowed to."""

    catalogue_service_id: UUID | None = None
    kind: DiscoveryArtifactKind | None = None
    host: str | None = None

    def conditions(self) -> list[ColumnElement[bool]]:
        """Return the where-clauses of the filters that are set."""
        pairs = (
            (DiscoveryArtifact.catalogue_service_id, self.catalogue_service_id),
            (DiscoveryArtifact.kind, self.kind),
            (func.lower(func.substring(DiscoveryArtifact.source_url, _URL_HOST)), self.host and self.host.lower()),
        )
        return [column == value for column, value in pairs if value is not None]


def _artifact_stmt(artifact_filter: ArtifactFilter) -> Select:
    return select(DiscoveryArtifact).where(*artifact_filter.conditions())


def _cited_by(candidate_id: UUID) -> ColumnElement[bool]:
    """Artifacts a mention of the candidate cites."""
    cited = select(DiscoveryCandidateMention.artifact_id).where(
        DiscoveryCandidateMention.candidate_id == candidate_id,
        DiscoveryCandidateMention.artifact_id.is_not(None),
    )
    return DiscoveryArtifact.id.in_(cited)


def _latest_screenshot_of_each_procedure(candidate_id: UUID) -> ColumnElement[bool]:
    """The newest screenshot of every procedure that mentions the candidate."""
    procedures = select(DiscoveryCandidateMention.catalogue_service_id).where(
        DiscoveryCandidateMention.candidate_id == candidate_id
    )
    latest = (
        select(DiscoveryArtifact.id)
        .where(
            DiscoveryArtifact.kind == DiscoveryArtifactKind.SCREENSHOT,
            DiscoveryArtifact.catalogue_service_id.in_(procedures),
        )
        .distinct(DiscoveryArtifact.catalogue_service_id)
        .order_by(DiscoveryArtifact.catalogue_service_id, DiscoveryArtifact.fetched_at.desc(), DiscoveryArtifact.id)
    )
    return DiscoveryArtifact.id.in_(latest)


def _candidate_evidence(candidate_id: UUID) -> Select:
    evidence = or_(_cited_by(candidate_id), _latest_screenshot_of_each_procedure(candidate_id))
    return select(DiscoveryArtifact).where(evidence)


class ArtifactListingRepository(SessionRepository):
    """List and count artifacts, newest fetch first."""

    def count_artifacts(self, artifact_filter: ArtifactFilter) -> int:
        """Count the artifacts that match ``artifact_filter``."""
        stmt = select(func.count()).select_from(_artifact_stmt(artifact_filter).subquery())
        return int(self._session.scalar(stmt) or 0)

    def list_artifacts_page(self, artifact_filter: ArtifactFilter, page: Page) -> list[DiscoveryArtifact]:
        """Return one page of artifacts matching ``artifact_filter``."""
        stmt = _artifact_stmt(artifact_filter).order_by(DiscoveryArtifact.fetched_at.desc(), DiscoveryArtifact.id)
        return list(self._session.scalars(stmt.offset(page.offset).limit(page.limit)).all())

    def count_candidate_artifacts(self, candidate_id: UUID) -> int:
        """Count the artifacts that are evidence for ``candidate_id``."""
        stmt = select(func.count()).select_from(_candidate_evidence(candidate_id).subquery())
        return int(self._session.scalar(stmt) or 0)

    def list_candidate_artifacts_page(self, candidate_id: UUID, page: Page) -> list[DiscoveryArtifact]:
        """Return one page of the cited artifacts and latest procedure screenshots of ``candidate_id``."""
        stmt = _candidate_evidence(candidate_id).order_by(DiscoveryArtifact.fetched_at.desc(), DiscoveryArtifact.id)
        return list(self._session.scalars(stmt.offset(page.offset).limit(page.limit)).all())
