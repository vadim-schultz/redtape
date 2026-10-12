"""Read models for discovery admin HTTP responses."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.discovery import (
    CatalogueService,
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


class CataloguePipelineResponse(BaseModel):
    """Pipeline drill-down aggregate; nested collections filled in later chapters."""

    service: CatalogueServiceRead
    tasks: list[DiscoveryTaskRead] = Field(default_factory=list)
    entities: list[dict[str, object]] = Field(default_factory=list)
    fetch_logs: list[dict[str, object]] = Field(default_factory=list)
    claims: list[dict[str, object]] = Field(default_factory=list)
    events: list[dict[str, object]] = Field(default_factory=list)
