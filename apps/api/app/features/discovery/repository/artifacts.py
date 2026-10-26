"""Discovery artifact persistence: lookups, inserts, byte totals and snapshot retention."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, select

from app.features.discovery.repository.base import SessionRepository
from app.models.discovery import DiscoveryArtifact, DiscoveryArtifactKind


@dataclass(frozen=True, slots=True)
class NewArtifact:
    """An artifact row to insert; the bytes are already in the object store."""

    catalogue_service_id: UUID
    discovery_task_id: UUID
    kind: DiscoveryArtifactKind
    storage_key: str
    sha256: str
    content_type: str
    byte_size: int
    source_url: str
    final_url: str | None
    fetched_at: datetime


class ArtifactRepository(SessionRepository):
    """Read and write ``discovery_artifact`` rows."""

    def find_artifact(self, catalogue_id: UUID, kind: DiscoveryArtifactKind, sha256: str) -> DiscoveryArtifact | None:
        """Return the artifact with the unique key ``(catalogue_id, kind, sha256)``, if any."""
        stmt = select(DiscoveryArtifact).where(
            DiscoveryArtifact.catalogue_service_id == catalogue_id,
            DiscoveryArtifact.kind == kind,
            DiscoveryArtifact.sha256 == sha256,
        )
        return self._session.scalar(stmt)

    def get_artifact(self, artifact_id: UUID) -> DiscoveryArtifact | None:
        """Return the artifact with ``artifact_id``, if any."""
        return self._session.get(DiscoveryArtifact, artifact_id)

    def insert_artifact(self, new: NewArtifact) -> DiscoveryArtifact:
        """Insert ``new`` and return the row."""
        row = DiscoveryArtifact(**asdict(new))
        self._session.add(row)
        self._session.flush()
        return row

    def total_artifact_bytes(self) -> int:
        """Return the summed ``byte_size`` of every artifact (the figure the storage cap is checked against)."""
        return int(self._session.scalar(select(func.coalesce(func.sum(DiscoveryArtifact.byte_size), 0))) or 0)

    def delete_old_snapshots(self, catalogue_id: UUID, *, keep: int) -> list[str]:
        """Delete all but the ``keep`` latest HTML snapshots of a catalogue row; return the deleted storage keys."""
        stale = (
            select(DiscoveryArtifact.id)
            .where(
                DiscoveryArtifact.catalogue_service_id == catalogue_id,
                DiscoveryArtifact.kind == DiscoveryArtifactKind.HTML_SNAPSHOT,
            )
            .order_by(DiscoveryArtifact.fetched_at.desc(), DiscoveryArtifact.created_at.desc(), DiscoveryArtifact.id)
            .offset(keep)
        )
        stmt = delete(DiscoveryArtifact).where(DiscoveryArtifact.id.in_(stale)).returning(DiscoveryArtifact.storage_key)
        return list(self._session.scalars(stmt))
