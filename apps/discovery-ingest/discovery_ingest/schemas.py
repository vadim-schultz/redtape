"""DTOs mirroring discovery machine API batch upsert."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, TypeGuard, get_args
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


class CatalogueMachineRead(BaseModel):
    """Minimal catalogue row from ``GET /catalogue/{id}`` for enrich workers."""

    id: UUID
    source: DiscoverySource
    portal_url: str | None = Field(default=None, max_length=500)
    title_i18n: dict[str, str] = Field(min_length=1)
    raw_payload: dict[str, object] = Field(default_factory=dict)


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


DiscoveryTaskKind = Literal["fetch_url", "enrich_metadata", "harvest_payload", "extract_page", "capture_screenshot"]
TASK_KINDS: tuple[DiscoveryTaskKind, ...] = get_args(DiscoveryTaskKind)
LEGACY_TASK_KINDS: tuple[DiscoveryTaskKind, ...] = ("fetch_url", "enrich_metadata")
WORKER_DEFAULT_TASK_KINDS: tuple[DiscoveryTaskKind, ...] = (*LEGACY_TASK_KINDS, "harvest_payload")


def is_task_kind(value: str) -> TypeGuard[DiscoveryTaskKind]:
    """Return whether ``value`` names a task kind the API knows."""
    return value in TASK_KINDS


DiscoveryTaskStatus = Literal["pending", "claimed", "completed", "failed"]


class TaskClaimRequest(BaseModel):
    """Body for ``POST /tasks/claim``."""

    limit: int = Field(default=1, ge=1, le=50)
    kinds: list[DiscoveryTaskKind] | None = Field(default=None, min_length=1)


class TaskEnqueueRequest(BaseModel):
    """Body for ``POST /tasks``: a follow-up task for one catalogue row."""

    catalogue_service_id: UUID
    kind: DiscoveryTaskKind
    target_url: str = Field(min_length=1, max_length=500)
    priority: int = Field(default=100, ge=0)
    input_key: str | None = Field(default=None, min_length=1, max_length=128)


class TaskEnqueueResponse(BaseModel):
    """The task behind an enqueue request."""

    id: UUID
    created: bool


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


class TaskSummary(BaseModel):
    """Queue counts for the requested kinds; ``claimed`` includes the ``claimed_stale`` leases."""

    pending_ready: int
    pending_delayed: int
    claimed: int
    claimed_stale: int
    completed: int
    failed: int


class FetchLogAppendRequest(BaseModel):
    """One HTTP fetch attempt against a task target."""

    http_status: int | None = None
    content_type: str | None = Field(default=None, max_length=200)
    byte_length: int | None = Field(default=None, ge=0)
    error_message: str | None = None


StopReason = Literal["queue_empty", "batch_limit", "time_budget", "error"]


class DrainReport(BaseModel):
    """JSON-serializable worker drain summary."""

    batches: int = 0
    claimed: int
    completed: int
    failed: int
    skipped: int
    remaining: int | None = None
    remaining_unknown: bool = True
    stop_reason: StopReason
    run_id: UUID | None = None
    succeeded: bool = True
    ledger_unavailable: bool = False


class RunStartResponse(BaseModel):
    """Run record opened by the machine API."""

    id: UUID


class RunFinishRequest(BaseModel):
    """Report that closes a worker run."""

    status: Literal["succeeded", "failed"]
    claimed_count: int
    completed_count: int
    failed_count: int
    skipped_count: int
    remaining_count: int | None = None
    stop_reason: StopReason | None = None
    error_detail: str | None = None
