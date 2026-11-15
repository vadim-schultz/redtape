"""Request and response models for discovery machine HTTP routes."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.discovery import (
    LEGACY_TASK_KINDS,
    DiscoveryClaimKind,
    DiscoveryRunKind,
    DiscoveryRunStage,
    DiscoverySource,
    DiscoveryTaskKind,
    DiscoveryTaskStatus,
)
from app.schema.discovery.emit import EmitCounts, EmitOutcome
from app.schema.locale.keys import LocaleKeyedMap


class CatalogueBatchItem(BaseModel):
    """One catalogue row in a machine batch upsert."""

    source: DiscoverySource
    external_id: str = Field(min_length=1, max_length=200)
    jurisdiction_id: UUID
    title_i18n: LocaleKeyedMap = Field(min_length=1)
    description_i18n: LocaleKeyedMap | None = None
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


def resolve_task_kinds(kinds: Sequence[DiscoveryTaskKind] | None) -> tuple[DiscoveryTaskKind, ...]:
    """Return the named kinds, or the legacy kinds when none were named."""
    return LEGACY_TASK_KINDS if kinds is None else tuple(kinds)


class TaskClaimRequest(BaseModel):
    """Claim pending discovery tasks for the caller API key."""

    limit: int = Field(default=1, ge=1, le=50)
    kinds: list[DiscoveryTaskKind] | None = Field(default=None, min_length=1)

    @property
    def resolved_kinds(self) -> tuple[DiscoveryTaskKind, ...]:
        """Return the requested kinds, or the legacy kinds when none were named."""
        return resolve_task_kinds(self.kinds)


class TaskSummaryResponse(BaseModel):
    """Queue counts for the requested kinds; ``claimed`` includes the ``claimed_stale`` leases.

    ``oldest_pending_age_seconds`` is ``null`` when no task is ready; ``completed_24h`` and ``failed_24h`` count the
    tasks finished in the last day.
    """

    pending_ready: int
    pending_delayed: int
    claimed: int
    claimed_stale: int
    completed: int
    failed: int
    oldest_pending_age_seconds: float | None
    completed_24h: int
    failed_24h: int


class TaskEnqueueRequest(BaseModel):
    """Enqueue a follow-up task for a catalogue row."""

    catalogue_service_id: UUID
    kind: DiscoveryTaskKind
    target_url: str = Field(min_length=1, max_length=500)
    priority: int = Field(default=100, ge=0)
    input_key: str | None = Field(default=None, min_length=1, max_length=128)
    artifact_id: UUID | None = None


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
    artifact_id: UUID | None = None
    input_key: str | None = None


class TaskClaimResponse(BaseModel):
    """Tasks claimed in one request."""

    items: list[ClaimedTaskRead]


class TaskCompleteRequest(BaseModel):
    """Optional note on why a task completed without producing anything (for example ``no_mentions``)."""

    note: str | None = Field(default=None, max_length=200)


class TaskReleaseRequest(BaseModel):
    """Hand a claimed task back because a limit, not the page, stopped the work."""

    reason: str = Field(min_length=1, max_length=1000)
    not_before: datetime | None = None


class TaskReleaseResponse(BaseModel):
    """Task returned to the pending queue."""

    id: UUID
    status: DiscoveryTaskStatus
    last_error: str


class TaskCompleteResponse(BaseModel):
    """Task marked completed."""

    id: UUID
    status: DiscoveryTaskStatus


class TaskFailRequest(BaseModel):
    """Failure reason for a discovery task."""

    error: str = Field(min_length=1)
    retryable: bool = False


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


class CatalogueEmitItemResult(EmitOutcome):
    """Outcome of emitting one staging claim."""

    claim_id: UUID


class CatalogueEmitResponse(EmitCounts):
    """Summary of a catalogue emit run."""

    items: list[CatalogueEmitItemResult]


class RunStartRequest(BaseModel):
    """Open a run record before the worker starts draining; the stage defaults to the kind."""

    kind: DiscoveryRunKind = DiscoveryRunKind.WORKER_DRAIN
    stage: DiscoveryRunStage | None = None


StopReason = Literal[
    "queue_empty",
    "batch_limit",
    "time_budget",
    "error",
    "browser_budget",
    "browser_quota",
    "storage_unavailable",
    "db_limit",
    "llm_budget",
    "llm_quota",
    "rate_limited",
]
"""Why a worker drain ended; mirrors the ingest worker's ``StopReason``."""


SpendResource = Literal[
    "r2_class_a",
    "r2_class_b",
    "browser_seconds",
    "neurons",
    "actions_minutes",
    "azure_translator_chars",
]
"""The budget ledger's resources, the only names a run may report spend against (see the budget resources)."""
SpendAmount = Annotated[float, Field(ge=0, allow_inf_nan=False)]


class RunFinishRequest(BaseModel):
    """Close a run with its report and the spend it made per budget resource."""

    status: Literal["succeeded", "failed"]
    claimed_count: int = Field(ge=0)
    completed_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    skipped_count: int = Field(ge=0)
    remaining_count: int | None = Field(default=None, ge=0)
    stop_reason: StopReason | None = None
    error_detail: str | None = Field(default=None, max_length=1000)
    spend: dict[SpendResource, SpendAmount] | None = None


class RunRead(BaseModel):
    """Run record returned to workers."""

    id: UUID
    kind: str
    status: str
    started_at: datetime
    finished_at: datetime | None = None
