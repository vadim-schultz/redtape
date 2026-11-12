"""Public reads of procedure pages for other features: the snapshot a page translates and the candidates it carries."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from app.features.discovery.artifact_read import LatestSnapshot
from app.features.discovery.repository import DiscoveryRepository
from app.models.discovery import DiscoveryArtifact


class ProcedurePageReads:
    """Read the latest snapshot and the candidates of procedure pages, without exposing the repository."""

    def __init__(self, repository: DiscoveryRepository) -> None:
        """Bind the reads to ``repository``."""
        self._repo = repository

    @classmethod
    def for_session(cls, session: Session) -> ProcedurePageReads:
        """Bind the reads to ``session``, the way other features reach discovery without importing its repositories."""
        return cls(DiscoveryRepository(session))

    def latest_snapshots(self, catalogue_ids: Sequence[UUID]) -> dict[UUID, LatestSnapshot]:
        """Return the newest HTML snapshot of each page in ``catalogue_ids`` that has one; pages without are absent."""
        rows = self._repo.latest_html_snapshots(list(catalogue_ids))
        return {row.catalogue_service_id: _snapshot(row) for row in rows}

    def latest_snapshots_after(self, after: UUID | None, limit: int) -> dict[UUID, LatestSnapshot]:
        """Return the newest HTML snapshot of the first ``limit`` pages after ``after`` that have one, in id order."""
        ids = self._repo.html_snapshot_catalogue_ids_after(after, limit)
        found = self.latest_snapshots(ids)
        return {catalogue_id: found[catalogue_id] for catalogue_id in ids}

    def candidate_ids_by_page(self, catalogue_ids: Sequence[UUID]) -> dict[UUID, tuple[UUID, ...]]:
        """Return the candidates that mention each page in ``catalogue_ids``; a page without any is absent."""
        return self._repo.candidate_ids_by_catalogue(list(catalogue_ids))


def _snapshot(row: DiscoveryArtifact) -> LatestSnapshot:
    return LatestSnapshot(row.id, row.sha256, row.source_url)
