"""Request and response models for the discovery artifact routes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from litestar.datastructures import UploadFile
from pydantic import BaseModel

from app.models.discovery import DiscoveryArtifactKind


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


class ArtifactSummaryRead(BaseModel):
    """The few artifact fields a mention shows next to its excerpt."""

    id: UUID
    kind: DiscoveryArtifactKind
    fetched_at: datetime


class MissingScreenshotResponse(BaseModel):
    """The newest HTML snapshot of each rendered catalogue row that has no screenshot yet, newest first."""

    items: list[ArtifactRead]


class AdminArtifactRead(ArtifactRead):
    """Artifact metadata with a short-lived download URL (``None`` while storage is unset)."""

    url: str | None


class ArtifactListResponse(BaseModel):
    """One page of artifact metadata."""

    items: list[ArtifactRead]
    total: int
    offset: int
    limit: int


class AdminArtifactListResponse(BaseModel):
    """One page of artifacts with download URLs."""

    items: list[AdminArtifactRead]
    total: int
    offset: int
    limit: int


class ArtifactStatusResponse(BaseModel):
    """Whether an upload would be accepted right now, with the byte accounting behind the answer."""

    storage_enabled: bool
    bytes_used: int
    bytes_cap: int
