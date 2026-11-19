"""Paged artifact listings for the machine and admin APIs."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import ColumnElement, ColumnExpressionArgument, Select, exists, func, or_, select
from sqlalchemy.orm import aliased

from app.features.discovery.repository.base import SessionRepository
from app.features.discovery.repository.task_listing import Page
from app.models.discovery import DiscoveryArtifact, DiscoveryArtifactKind, DiscoveryCandidateMention

_URL_HOST = r"^[a-zA-Z][a-zA-Z0-9+.-]*://([^/?#:]+)"


def url_host(column: ColumnExpressionArgument[str]) -> ColumnElement[str]:
    """Return the lower-case host of the URL in ``column``, the expression ``host`` filters compare."""
    return func.lower(func.substring(column, _URL_HOST))


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
            (url_host(DiscoveryArtifact.source_url), self.host and self.host.lower()),
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
    """Match the newest screenshot of every procedure that mentions the candidate."""
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


def _has_screenshot() -> ColumnElement[bool]:
    """Match a catalogue row that has at least one screenshot."""
    shot = aliased(DiscoveryArtifact)
    return exists().where(
        shot.catalogue_service_id == DiscoveryArtifact.catalogue_service_id,
        shot.kind == DiscoveryArtifactKind.SCREENSHOT,
    )


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

    def html_snapshots_without_screenshot(self, catalogue_id: UUID | None, limit: int) -> list[DiscoveryArtifact]:
        """Return the newest HTML snapshot of each rendered catalogue row with no screenshot, newest first, at most ``limit``."""
        newest = (
            select(DiscoveryArtifact.id)
            .where(
                *ArtifactFilter(
                    catalogue_service_id=catalogue_id, kind=DiscoveryArtifactKind.HTML_SNAPSHOT
                ).conditions()
            )
            .distinct(DiscoveryArtifact.catalogue_service_id)
            .order_by(
                DiscoveryArtifact.catalogue_service_id,
                DiscoveryArtifact.fetched_at.desc(),
                DiscoveryArtifact.created_at.desc(),
                DiscoveryArtifact.id,
            )
        )
        stmt = (
            select(DiscoveryArtifact)
            .where(DiscoveryArtifact.id.in_(newest), ~_has_screenshot())
            .order_by(DiscoveryArtifact.fetched_at.desc(), DiscoveryArtifact.id)
            .limit(limit)
        )
        return list(self._session.scalars(stmt).all())

    def count_candidate_artifacts(self, candidate_id: UUID) -> int:
        """Count the artifacts that are evidence for ``candidate_id``."""
        stmt = select(func.count()).select_from(_candidate_evidence(candidate_id).subquery())
        return int(self._session.scalar(stmt) or 0)

    def list_candidate_artifacts_page(self, candidate_id: UUID, page: Page) -> list[DiscoveryArtifact]:
        """Return one page of the cited artifacts and latest procedure screenshots of ``candidate_id``."""
        stmt = _candidate_evidence(candidate_id).order_by(DiscoveryArtifact.fetched_at.desc(), DiscoveryArtifact.id)
        return list(self._session.scalars(stmt.offset(page.offset).limit(page.limit)).all())
