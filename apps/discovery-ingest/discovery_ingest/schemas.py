"""DTOs mirroring discovery machine API batch upsert."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

DiscoverySource = Literal["govdata", "pvog", "fim", "leika", "manual"]


class CatalogueBatchItem(BaseModel):
    """One catalogue row for ``POST /catalogue/batch``."""

    source: DiscoverySource
    external_id: str = Field(min_length=1, max_length=200)
    jurisdiction_id: UUID
    title_i18n: dict[str, str] = Field(min_length=1)
    description_i18n: dict[str, str] | None = None
    portal_url: str | None = Field(default=None, max_length=500)
    raw_payload: dict[str, object] = Field(default_factory=dict)


class CatalogueBatchRequest(BaseModel):
    """Batch upsert body."""

    items: list[CatalogueBatchItem] = Field(min_length=1, max_length=50)


DiscoveryClaimKind = Literal["new_document", "new_requirement", "metadata"]


class EntityUpsertRequest(BaseModel):
    """Body for ``POST /entities``."""

    catalogue_service_id: UUID
    canonical_url: str = Field(min_length=1, max_length=500)
    label: str | None = Field(default=None, max_length=500)


class EntityUpsertResponse(BaseModel):
    """Upsert outcome for one entity."""

    id: UUID
    catalogue_service_id: UUID
    canonical_url: str
    created: bool


class ClaimAppendRequest(BaseModel):
    """Body for ``POST /claims``."""

    discovery_entity_id: UUID
    kind: DiscoveryClaimKind
    payload: dict[str, object] = Field(default_factory=dict)
    confidence: float | None = Field(default=None, ge=0, le=1)


class ClaimAppendResponse(BaseModel):
    """Created discovery claim row."""

    id: UUID
    discovery_entity_id: UUID
    kind: DiscoveryClaimKind


DiscoveryTaskKind = Literal["fetch_url", "enrich_metadata"]
DiscoveryTaskStatus = Literal["pending", "claimed", "completed", "failed"]


class TaskClaimRequest(BaseModel):
    """Body for ``POST /tasks/claim``."""

    limit: int = Field(default=1, ge=1, le=50)


class ClaimedTask(BaseModel):
    """Task assigned to the caller with an active lease."""

    id: UUID
    catalogue_service_id: UUID
    kind: DiscoveryTaskKind
    target_url: str
    status: DiscoveryTaskStatus
    priority: int
    lease_expires_at: datetime


class TaskClaimResponse(BaseModel):
    """Tasks claimed in one request."""

    items: list[ClaimedTask]


class FetchLogAppendRequest(BaseModel):
    """One HTTP fetch attempt against a task target."""

    http_status: int | None = None
    content_type: str | None = Field(default=None, max_length=200)
    byte_length: int | None = Field(default=None, ge=0)
    error_message: str | None = None


class DrainReport(BaseModel):
    """JSON-serializable worker drain summary."""

    claimed: int
    completed: int
    failed: int
    skipped: int
