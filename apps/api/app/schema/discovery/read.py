"""Read models for discovery admin HTTP responses."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from app.models.discovery import (
    DiscoveryCandidateStatus,
    DiscoveryClaimKind,
    DiscoveryEventType,
    DiscoveryMentionRole,
    DiscoverySource,
    DiscoveryTaskKind,
    DiscoveryTaskStatus,
)
from app.schema.candidate import CandidateFlags
from app.schema.discovery.artifacts import ArtifactSummaryRead
from app.schema.discovery.candidates import PvogSourcePath
from app.schema.discovery.emit import SkipReason

JsonObject = dict[str, JsonValue]


class DiscoveryTaskRead(BaseModel):
    """Queued fetch or enrich work visible in the admin crawler queue."""

    model_config = ConfigDict(from_attributes=False)

    id: UUID
    catalogue_service_id: UUID
    source: DiscoverySource
    kind: DiscoveryTaskKind
    target_url: str
    status: DiscoveryTaskStatus
    priority: int
    attempt_count: int
    not_before: datetime | None
    input_key: str | None
    result_note: str | None
    lease_expires_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DiscoveryTaskListResponse(BaseModel):
    """Paginated discovery task queue."""

    items: list[DiscoveryTaskRead]
    total: int
    offset: int
    limit: int


class CatalogueServiceRead(BaseModel):
    """Imported catalogue row in the admin index."""

    model_config = ConfigDict(from_attributes=False)

    id: UUID
    source: DiscoverySource
    external_id: str
    jurisdiction_id: UUID
    title_i18n: dict[str, str]
    pipeline_stage: str
    portal_url: str | None
    created_at: datetime
    updated_at: datetime


class CatalogueSummaryChips(BaseModel):
    """Aggregate counts for catalogue index chips."""

    total: int
    by_source: dict[str, int] = Field(default_factory=dict)
    by_pipeline_stage: dict[str, int] = Field(default_factory=dict)


class CatalogueListResponse(BaseModel):
    """Paginated catalogue index with summary chips."""

    items: list[CatalogueServiceRead]
    summary: CatalogueSummaryChips
    total: int
    offset: int
    limit: int


class TaskCountsRead(BaseModel):
    """Task totals grouped by current status."""

    total: int
    pending: int
    claimed: int
    completed: int
    failed: int


class CandidateCountsRead(BaseModel):
    """Document candidate totals by lifecycle status, plus their mentions."""

    total: int
    staged: int
    emitted: int
    mentions: int


class LlmOutcomesRead(BaseModel):
    """Completed ``llm_extract`` tasks by what the model run produced."""

    extracted: int
    no_documents: int
    login_wall: int
    no_content: int


class ArtifactTotalsRead(BaseModel):
    """Artifact count and stored bytes of one kind."""

    count: int
    bytes: int


class ArtifactCoverageRead(BaseModel):
    """Stored artifacts per kind against the storage cap."""

    by_kind: dict[str, ArtifactTotalsRead]
    total_bytes: int
    bytes_cap: int


class DiscoveryRunRead(BaseModel):
    """Operational run record as shown to operators."""

    id: UUID
    kind: str
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    claimed_count: int
    completed_count: int
    failed_count: int
    skipped_count: int
    remaining_count: int | None = None
    stop_reason: str | None = None
    error_detail: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DiscoveryCoverageResponse(BaseModel):
    """Operational queue and ingest counts for the admin coverage surface."""

    by_source: dict[str, int] = Field(default_factory=dict)
    tasks_pending: int
    tasks_failed: int
    emit_ready_count: int
    task_counts: TaskCountsRead
    task_counts_by_kind: dict[str, TaskCountsRead] = Field(default_factory=dict)
    candidates: CandidateCountsRead
    llm_outcomes: LlmOutcomesRead
    artifacts: ArtifactCoverageRead
    fetch_attempts_total: int
    stale_claims: int
    stale_runs: int
    failures_by_source: dict[str, int] = Field(default_factory=dict)
    last_successful_run: DiscoveryRunRead | None = None


class EmitPreviewItemRead(BaseModel):
    """One would-be suggestion emit row for admin review."""

    claim_id: UUID
    kind: str
    payload: dict[str, object] | None = None
    skip_reason: SkipReason | None = None


class EmitPreviewResponse(BaseModel):
    """Read-only preview of suggestion payloads for a catalogue service."""

    items: list[EmitPreviewItemRead]


class PipelineEntityRow(BaseModel):
    """A canonical entity a catalogue service's pipeline has staged."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    catalogue_service_id: UUID
    canonical_url: str
    label: str | None
    created_at: datetime


class FetchLogRow(BaseModel):
    """One fetch attempt of a discovery task."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    discovery_task_id: UUID
    http_status: int | None
    fetched_at: datetime
    content_type: str | None
    byte_length: int | None
    error_message: str | None


class ClaimRow(BaseModel):
    """One claim extracted from an entity; the payload is open JSON."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    discovery_entity_id: UUID
    kind: DiscoveryClaimKind
    payload: JsonObject
    confidence: float | None
    created_at: datetime


class EventRow(BaseModel):
    """One audit event about a catalogue service or a task."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    event_type: DiscoveryEventType
    catalogue_service_id: UUID | None
    discovery_task_id: UUID | None
    payload: JsonObject
    created_at: datetime


class CataloguePipelineResponse(BaseModel):
    """Pipeline drill-down aggregate for one catalogue service."""

    service: CatalogueServiceRead
    derived_stage: str
    tasks: list[DiscoveryTaskRead] = Field(default_factory=list)
    entities: list[PipelineEntityRow] = Field(default_factory=list)
    fetch_logs: list[FetchLogRow] = Field(default_factory=list)
    claims: list[ClaimRow] = Field(default_factory=list)
    events: list[EventRow] = Field(default_factory=list)


class CandidateRead(BaseModel):
    """Document candidate with the number of procedures mentioning it."""

    model_config = ConfigDict(from_attributes=False)

    id: UUID
    jurisdiction_id: UUID
    key: str
    title_i18n: dict[str, str]
    official_url: str | None
    status: DiscoveryCandidateStatus
    suggestion_id: UUID | None
    mention_count: int
    created_at: datetime
    updated_at: datetime


class CandidateListItemRead(CandidateRead):
    """A listed candidate with its roles, jurisdiction name and completeness flags."""

    roles: list[DiscoveryMentionRole]
    jurisdiction_name_i18n: dict[str, str]
    completeness: int
    complete: bool
    flags: CandidateFlags


class CandidateListResponse(BaseModel):
    """Paginated document candidates."""

    items: list[CandidateListItemRead]
    total: int
    offset: int
    limit: int


class CandidateMentionRead(BaseModel):
    """One mention with the procedure it was found in."""

    model_config = ConfigDict(from_attributes=False)

    id: UUID
    catalogue_service_id: UUID
    procedure_title_i18n: dict[str, str]
    procedure_source: DiscoverySource
    portal_url: str | None
    role: DiscoveryMentionRole
    excerpt: str
    source_field: str
    artifact_id: UUID | None
    artifact: ArtifactSummaryRead | None
    extractor: str
    extractor_version: str
    condition: str | None
    is_optional: bool | None
    category_codes: list[str]
    unknown_category_codes: list[str]
    pvog_leaf_code: str | None
    direct_category_confidence: float | None
    pvog_source_path: PvogSourcePath | None
    pvog_mapping_version: str | None
    created_at: datetime


class TagSupportRead(BaseModel):
    """How many procedures carry a code, their share of the tagged procedures, and its combined score."""

    code: str
    procedures: int
    share: float
    score: float


class CandidateDetailResponse(BaseModel):
    """A candidate with its jurisdiction name, every mention and the tag consensus of those mentions."""

    candidate: CandidateRead
    jurisdiction_name_i18n: dict[str, str]
    mentions: list[CandidateMentionRead]
    suggested_category_codes: list[TagSupportRead]
