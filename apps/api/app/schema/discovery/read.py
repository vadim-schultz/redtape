"""Read models for discovery admin HTTP responses."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.discovery import (
    CatalogueService,
    DiscoveryCandidateMention,
    DiscoveryCandidateStatus,
    DiscoveryDocumentCandidate,
    DiscoveryMentionRole,
    DiscoverySource,
    DiscoveryTask,
    DiscoveryTaskKind,
    DiscoveryTaskStatus,
)


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
    lease_expires_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_row(cls, task: DiscoveryTask, *, source: DiscoverySource) -> DiscoveryTaskRead:
        return cls(
            id=task.id,
            catalogue_service_id=task.catalogue_service_id,
            source=source,
            kind=task.kind,
            target_url=task.target_url,
            status=task.status,
            priority=task.priority,
            attempt_count=task.attempt_count,
            not_before=task.not_before,
            input_key=task.input_key,
            lease_expires_at=task.lease_expires_at,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )


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

    @classmethod
    def from_row(cls, row: CatalogueService) -> CatalogueServiceRead:
        return cls(
            id=row.id,
            source=row.source,
            external_id=row.external_id,
            jurisdiction_id=row.jurisdiction_id,
            title_i18n=row.title_i18n,
            pipeline_stage=row.pipeline_stage,
            portal_url=row.portal_url,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


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
    skip_reason: str | None = None


class EmitPreviewResponse(BaseModel):
    """Read-only preview of suggestion payloads for a catalogue service."""

    items: list[EmitPreviewItemRead]


class CataloguePipelineResponse(BaseModel):
    """Pipeline drill-down aggregate for one catalogue service."""

    service: CatalogueServiceRead
    derived_stage: str
    tasks: list[DiscoveryTaskRead] = Field(default_factory=list)
    entities: list[dict[str, object]] = Field(default_factory=list)
    fetch_logs: list[dict[str, object]] = Field(default_factory=list)
    claims: list[dict[str, object]] = Field(default_factory=list)
    events: list[dict[str, object]] = Field(default_factory=list)


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

    @classmethod
    def from_row(cls, row: DiscoveryDocumentCandidate, *, mention_count: int) -> CandidateRead:
        return cls(
            id=row.id,
            jurisdiction_id=row.jurisdiction_id,
            key=row.key,
            title_i18n=row.title_i18n,
            official_url=row.official_url,
            status=row.status,
            suggestion_id=row.suggestion_id,
            mention_count=mention_count,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


class CandidateListResponse(BaseModel):
    """Paginated document candidates."""

    items: list[CandidateRead]
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
    extractor: str
    extractor_version: str
    created_at: datetime

    @classmethod
    def from_row(cls, mention: DiscoveryCandidateMention, procedure: CatalogueService) -> CandidateMentionRead:
        return cls(
            id=mention.id,
            catalogue_service_id=procedure.id,
            procedure_title_i18n=procedure.title_i18n,
            procedure_source=procedure.source,
            portal_url=procedure.portal_url,
            role=mention.role,
            excerpt=mention.excerpt,
            source_field=mention.source_field,
            artifact_id=mention.artifact_id,
            extractor=mention.extractor,
            extractor_version=mention.extractor_version,
            created_at=mention.created_at,
        )


class CandidateDetailResponse(BaseModel):
    """A candidate with every mention."""

    candidate: CandidateRead
    mentions: list[CandidateMentionRead]
