"""Paged artifact listings for the machine and admin APIs."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import ColumnElement, Select, func, select

from app.features.discovery.repository.base import SessionRepository
from app.features.discovery.repository.task_listing import Page
from app.models.discovery import DiscoveryArtifact, DiscoveryArtifactKind

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
