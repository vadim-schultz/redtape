"""Request and response models for the discovery artifact routes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from litestar.datastructures import UploadFile
from pydantic import BaseModel

from app.models.discovery import DiscoveryArtifact, DiscoveryArtifactKind


@dataclass
class ArtifactUploadForm:
    """Multipart body of an artifact upload. A client-supplied hash is not a field and is ignored."""

    file: UploadFile
    kind: DiscoveryArtifactKind
    source_url: str
    final_url: str | None = None
    fetched_at: datetime | None = None


class ArtifactRead(BaseModel):
    """Artifact metadata; the bytes stay in the object store."""

    id: UUID
    catalogue_service_id: UUID
    discovery_task_id: UUID | None
    kind: DiscoveryArtifactKind
    storage_key: str
    sha256: str
    content_type: str
    byte_size: int
    source_url: str
    final_url: str | None
    fetched_at: datetime
    created_at: datetime

    @classmethod
    def from_row(cls, row: DiscoveryArtifact) -> ArtifactRead:
        """Build the metadata view of ``row``."""
        return cls.model_validate(row, from_attributes=True)
