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


class ArtifactPage(BaseModel):
    """One page of artifact metadata from the machine list route."""

    items: list[ArtifactRead]
    total: int
    offset: int
    limit: int


class MissingScreenshotPage(BaseModel):
    """Rendered pages with no screenshot yet, each as its newest HTML snapshot, from the missing-screenshot route."""

    items: list[ArtifactRead]


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
class ArtifactQuery:
    """One page of stored artifacts of ``kind``; ``host`` is the source host, any host when ``None``."""

    host: str | None
    kind: ArtifactKind
    offset: int
    limit: int


@dataclass(frozen=True, slots=True)
class ArtifactContent:
    """The stored bytes of an artifact with the ``Content-Type`` the content route answered with."""

    data: bytes
    content_type: str | None
