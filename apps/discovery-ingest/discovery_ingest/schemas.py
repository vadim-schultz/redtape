"""DTOs mirroring discovery machine API batch upsert."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Final, Literal, TypeGuard, get_args
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


DiscoveryTaskKind = Literal[
    "fetch_url",
    "enrich_metadata",
    "harvest_payload",
    "extract_page",
    "render_page",
    "capture_screenshot",
    "llm_extract",
]
TASK_KINDS: tuple[DiscoveryTaskKind, ...] = get_args(DiscoveryTaskKind)
LEGACY_TASK_KINDS: tuple[DiscoveryTaskKind, ...] = ("fetch_url", "enrich_metadata")
BROWSER_TASK_KINDS: tuple[DiscoveryTaskKind, ...] = ("render_page", "capture_screenshot")
"""Kinds that spend Cloudflare browser time; never in the default kinds."""
LLM_TASK_KINDS: tuple[DiscoveryTaskKind, ...] = ("llm_extract",)
"""Kinds that spend Workers AI neurons; never in the default kinds."""
WORKER_DEFAULT_TASK_KINDS: tuple[DiscoveryTaskKind, ...] = (*LEGACY_TASK_KINDS, "harvest_payload", "extract_page")


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
    artifact_id: UUID | None = None


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
    artifact_id: UUID | None = None
    input_key: str | None = None


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
    released: int = 0
    stale: int = 0
    rejected: int = 0
    unavailable: int = 0
    repaired: int = 0
    invalid: int = 0
    unchanged: int = 0
    pruned: int = 0
    untranslated_blocks: int = 0
    browser_seconds_used: float = 0.0
    neurons_used: float = 0.0
    llm_calls: int = 0
    tokens_used: int = 0
    characters_used: int = 0
    auth_mode: str | None = None
    render_enqueue_failed: int = 0
    capture_enqueue_failed: int = 0
    llm_enqueue_failed: int = 0
    error: str | None = None


class RunStartResponse(BaseModel):
    """Run record opened by the machine API."""

    id: UUID


RunStage = Literal["worker_drain", "embed", "translate", "snapshot_translate"]
"""The drain a run record belongs to; the API defaults a run that names none to its kind."""


class RunFinishRequest(BaseModel):
    """Report that closes a worker run, with the spend per budget resource the drain made."""

    status: Literal["succeeded", "failed"]
    claimed_count: int = Field(ge=0)
    completed_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    skipped_count: int = Field(ge=0)
    remaining_count: int | None = Field(default=None, ge=0)
    stop_reason: StopReason | None = None
    error_detail: str | None = Field(default=None, max_length=1000)
    spend: dict[str, float] | None = None


MAX_SNAPSHOT_BATCH: Final = 5
"""Most snapshot tasks one claim hands out and most items one complete call carries: the API's 2 MiB body cap allows five."""


class SnapshotClaimRequest(BaseModel):
    """Claim up to ``limit`` pending page tasks, highest-priority pages first."""

    limit: int = Field(default=MAX_SNAPSHOT_BATCH, ge=1, le=MAX_SNAPSHOT_BATCH)


class ClaimedSnapshotTask(BaseModel):
    """One leased page task: the artifact to read, its raw sha, and the cleaned-text hash already stored, if any."""

    task_id: UUID
    catalogue_service_id: UUID
    locale: str
    source_locale: Literal["de"] = "de"
    artifact_id: UUID
    artifact_sha256: str
    source_url: str
    stored_source_hash: str | None
    lease_expires_at: datetime


class SnapshotClaimResponse(BaseModel):
    """The page tasks one claim leased."""

    items: list[ClaimedSnapshotTask]


class SnapshotTextBlock(BaseModel):
    """A block of translated text: a heading, a paragraph, a list item or a definition term."""

    kind: Literal["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "dt"]
    text: str
    untranslated: bool = False
    """True when the translation was refused and the German text was kept in its place."""


class SnapshotRowBlock(BaseModel):
    """A table row: its cells in source order."""

    kind: Literal["row"]
    cells: list[str]
    untranslated: bool = False
    """True when any cell was refused and kept its German text."""


SnapshotWireBlock = Annotated[SnapshotTextBlock | SnapshotRowBlock, Field(discriminator="kind")]
"""One block of a page on the wire, discriminated by its kind; a row carries cells, every other kind carries text."""


class SnapshotCompleteItem(BaseModel):
    """The result for one claimed page: a translated, unchanged or skipped outcome, with the fields that outcome carries."""

    task_id: UUID
    artifact_sha256: str = Field(min_length=64, max_length=64)
    source_hash: str = Field(min_length=1, max_length=64)
    outcome: Literal["translated", "unchanged", "skipped"]
    blocks: list[SnapshotWireBlock] | None = None
    truncated: bool = False
    engine: str | None = Field(default=None, min_length=1, max_length=50)
    model: str | None = Field(default=None, max_length=100)
    skipped_reason: Literal["too_short", "not_german"] | None = None


class SnapshotCompleteRequest(BaseModel):
    """A batch of page results, at most five, so the body stays under the 2 MiB cap."""

    items: list[SnapshotCompleteItem] = Field(min_length=1, max_length=MAX_SNAPSHOT_BATCH)


class SnapshotItemResult(BaseModel):
    """What completing one page did; ``reason`` explains a stale, rejected or unavailable answer."""

    task_id: UUID
    outcome: Literal["stored", "unchanged", "skipped", "stale", "rejected", "unavailable"]
    reason: str | None = None


class SnapshotCompleteResponse(BaseModel):
    """One result per submitted item, in request order."""

    items: list[SnapshotItemResult]


class SnapshotLocaleSummary(BaseModel):
    """Queue and store counts of one target locale for snapshot pages."""

    locale: str
    pending_ready: int
    claimed: int
    failed: int
    translated: int
    stale: int
    skipped: int


class SnapshotSummaryResponse(BaseModel):
    """Counts per target locale, so a workflow can stop early when no page is ready."""

    locales: list[SnapshotLocaleSummary]

    @property
    def pending_ready(self) -> int:
        """Pages ready to be claimed across every target locale."""
        return sum(row.pending_ready for row in self.locales)
