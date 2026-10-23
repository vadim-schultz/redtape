"""Request and response models for discovery machine HTTP routes."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.discovery import (
    LEGACY_TASK_KINDS,
    DiscoveryClaimKind,
    DiscoveryRunKind,
    DiscoverySource,
    DiscoveryTaskKind,
    DiscoveryTaskStatus,
)


class CatalogueBatchItem(BaseModel):
    """One catalogue row in a machine batch upsert."""

    source: DiscoverySource
    external_id: str = Field(min_length=1, max_length=200)
    jurisdiction_id: UUID
    title_i18n: dict[str, str] = Field(min_length=1)
    description_i18n: dict[str, str] | None = None
    portal_url: str | None = Field(default=None, max_length=500)
    raw_payload: dict[str, object] = Field(default_factory=dict)


class CatalogueBatchRequest(BaseModel):
    """Batch upsert body for ingest workers."""

    items: list[CatalogueBatchItem] = Field(min_length=1, max_length=50)


class CatalogueBatchItemResult(BaseModel):
    """Upsert outcome for a single catalogue row."""

    id: UUID
    source: DiscoverySource
    external_id: str
    task_id: UUID | None = None


class CatalogueBatchResponse(BaseModel):
    """Batch upsert summary."""

    items: list[CatalogueBatchItemResult]


class CatalogueMachineRead(BaseModel):
    """Minimal catalogue row for ingest enrich workers."""

    id: UUID
    source: DiscoverySource
    portal_url: str | None = Field(default=None, max_length=500)
    title_i18n: dict[str, str] = Field(min_length=1)
    raw_payload: dict[str, object] = Field(default_factory=dict)


class TaskClaimRequest(BaseModel):
    """Claim pending discovery tasks for the caller API key."""

    limit: int = Field(default=1, ge=1, le=50)
    kinds: list[DiscoveryTaskKind] | None = Field(default=None, min_length=1)

    @property
    def resolved_kinds(self) -> tuple[DiscoveryTaskKind, ...]:
        """Return the requested kinds, or the legacy kinds when none were named."""
        return LEGACY_TASK_KINDS if self.kinds is None else tuple(self.kinds)


class TaskEnqueueRequest(BaseModel):
    """Enqueue a follow-up task for a catalogue row."""

    catalogue_service_id: UUID
    kind: DiscoveryTaskKind
    target_url: str = Field(min_length=1, max_length=500)
    priority: int = Field(default=100, ge=0)
    input_key: str | None = Field(default=None, min_length=1, max_length=128)


class TaskEnqueueResponse(BaseModel):
    """The task behind an enqueue request."""

    id: UUID
    created: bool


class ClaimedTaskRead(BaseModel):
    """Task assigned to the caller with an active lease."""

    model_config = ConfigDict(from_attributes=False)

    id: UUID
    catalogue_service_id: UUID
    kind: DiscoveryTaskKind
    target_url: str
    status: DiscoveryTaskStatus
    priority: int
    lease_expires_at: datetime


class TaskClaimResponse(BaseModel):
    """Tasks claimed in one request."""

    items: list[ClaimedTaskRead]


class TaskCompleteResponse(BaseModel):
    """Task marked completed."""

    id: UUID
    status: DiscoveryTaskStatus


class TaskFailRequest(BaseModel):
    """Failure reason for a discovery task."""

    error: str = Field(min_length=1)


class TaskFailResponse(BaseModel):
    """Task marked failed."""

    id: UUID
    status: DiscoveryTaskStatus
    last_error: str


class FetchLogAppendRequest(BaseModel):
    """One HTTP fetch attempt against a task target."""

    http_status: int | None = None
    content_type: str | None = Field(default=None, max_length=200)
    byte_length: int | None = Field(default=None, ge=0)
    error_message: str | None = None


class FetchLogAppendResponse(BaseModel):
    """Created fetch log row."""

    id: UUID
    discovery_task_id: UUID
    task_status: DiscoveryTaskStatus


class EntityUpsertRequest(BaseModel):
    """Upsert a discovery entity under an existing catalogue row."""

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
    """Append a validated claim on a discovery entity."""

    discovery_entity_id: UUID
    kind: DiscoveryClaimKind
    payload: dict[str, object] = Field(default_factory=dict)
    confidence: float | None = Field(default=None, ge=0, le=1)


class ClaimAppendResponse(BaseModel):
    """Created discovery claim row."""

    id: UUID
    discovery_entity_id: UUID
    kind: DiscoveryClaimKind


class CatalogueEmitItemResult(BaseModel):
    """Outcome of emitting one staging claim."""

    claim_id: UUID
    suggestion_id: UUID | None = None
    skip_reason: str | None = None
    replayed: bool = False


class CatalogueEmitResponse(BaseModel):
    """Summary of a catalogue emit run."""

    items: list[CatalogueEmitItemResult]
    created_count: int
    skipped_count: int
    replayed_count: int


class RunStartRequest(BaseModel):
    """Open a run record before the worker starts draining."""

    kind: DiscoveryRunKind = DiscoveryRunKind.WORKER_DRAIN


class RunFinishRequest(BaseModel):
    """Close a run with its report."""

    status: Literal["succeeded", "failed"]
    claimed_count: int = Field(ge=0)
    completed_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    skipped_count: int = Field(ge=0)
    remaining_count: int | None = Field(default=None, ge=0)
    stop_reason: Literal["queue_empty", "batch_limit", "time_budget", "error"] | None = None
    error_detail: str | None = Field(default=None, max_length=1000)


class RunRead(BaseModel):
    """Run record returned to workers."""

    id: UUID
    kind: str
    status: str
    started_at: datetime
    finished_at: datetime | None = None
