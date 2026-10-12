"""Discovery admin read orchestration."""

from __future__ import annotations

from uuid import UUID

from app.features.discovery.repository import DiscoveryRepository
from app.models.discovery import DiscoverySource, DiscoveryTaskStatus
from app.schema.discovery.read import (
    CatalogueListResponse,
    CataloguePipelineResponse,
    CatalogueServiceRead,
    CatalogueSummaryChips,
    DiscoveryTaskListResponse,
    DiscoveryTaskRead,
)


class DiscoveryAdminService:
    """Read-only discovery data for allowlisted operators."""

    def __init__(self, repository: DiscoveryRepository) -> None:
        self._repo = repository

    def list_tasks(
        self,
        *,
        status: DiscoveryTaskStatus | None,
        source: DiscoverySource | None,
        offset: int,
        limit: int,
    ) -> DiscoveryTaskListResponse:
        total = self._repo.count_tasks(status=status, source=source)
        rows = self._repo.list_tasks_page(offset=offset, limit=limit, status=status, source=source)
        items = [DiscoveryTaskRead.from_row(task, source=task_source) for task, task_source in rows]
        return DiscoveryTaskListResponse(items=items, total=total, offset=offset, limit=limit)

    def list_catalogue(
        self,
        *,
        source: DiscoverySource | None,
        offset: int,
        limit: int,
    ) -> CatalogueListResponse:
        total = self._repo.count_catalogue(source=source)
        rows = self._repo.list_catalogue_page(offset=offset, limit=limit, source=source)
        items = [CatalogueServiceRead.from_row(row) for row in rows]
        chip_total, by_source, by_stage = self._repo.catalogue_summary(source=source)
        summary = CatalogueSummaryChips(total=chip_total, by_source=by_source, by_pipeline_stage=by_stage)
        return CatalogueListResponse(items=items, summary=summary, total=total, offset=offset, limit=limit)

    def pipeline_stub(self, catalogue_id: UUID) -> CataloguePipelineResponse | None:
        row = self._repo.get_catalogue(catalogue_id)
        if row is None:
            return None
        return CataloguePipelineResponse(service=CatalogueServiceRead.from_row(row))
