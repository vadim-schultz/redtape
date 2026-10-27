"""Artifact payloads exchanged with the machine API: what a worker uploads and what the API answers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

ArtifactKind = Literal["html_snapshot", "screenshot"]


class ArtifactRead(BaseModel):
    """Artifact metadata; the bytes stay in the object store."""

    id: UUID
    catalogue_service_id: UUID
    discovery_task_id: UUID | None
    kind: ArtifactKind
    sha256: str
    content_type: str
    byte_size: int
    source_url: str
    final_url: str | None
    fetched_at: datetime


class ArtifactStatus(BaseModel):
    """Whether an upload would be accepted right now."""

    storage_enabled: bool
    bytes_used: int
    bytes_cap: int


@dataclass(frozen=True, slots=True)
class ArtifactUpload:
    """One file to store for a task; ``final_url`` is optional."""

    kind: ArtifactKind
    data: bytes
    content_type: str
    source_url: str
    final_url: str | None
    fetched_at: datetime


@dataclass(frozen=True, slots=True)
class StoredArtifact:
    """The artifact behind an upload; ``created`` is false when identical bytes were already stored."""

    artifact: ArtifactRead
    created: bool


@dataclass(frozen=True, slots=True)
class ArtifactContent:
    """The stored bytes of an artifact with the ``Content-Type`` the content route answered with."""

    data: bytes
    content_type: str | None
