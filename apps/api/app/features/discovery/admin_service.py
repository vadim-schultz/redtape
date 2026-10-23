"""Read-only discovery admin queries for allowlisted operators."""

from __future__ import annotations

from dataclasses import asdict
from uuid import UUID

from app.features.discovery.emit_preview import build_emit_preview_items
from app.features.discovery.lookups import require_catalogue
from app.features.discovery.pipeline_rows import (
    claim_dict,
    entity_dict,
    event_dict,
    fetch_log_dict,
    stage_of,
)
from app.features.discovery.repository import DiscoveryRepository, Page
from app.models.discovery import DiscoverySource, DiscoveryTaskStatus
from app.schema.discovery.read import (
    CatalogueListResponse,
    CataloguePipelineResponse,
    CatalogueServiceRead,
    CatalogueSummaryChips,
    DiscoveryCoverageResponse,
    DiscoveryRunRead,
    DiscoveryTaskListResponse,
    DiscoveryTaskRead,
    EmitPreviewItemRead,
    EmitPreviewResponse,
    TaskCountsRead,
)


class DiscoveryAdminService:
    """Read-only discovery data for allowlisted operators."""

    def __init__(self, repository: DiscoveryRepository) -> None:
        """Bind the service to ``repository``."""
        self._repo = repository

    def list_tasks(
        self,
        *,
        status: DiscoveryTaskStatus | None,
        source: DiscoverySource | None,
        offset: int,
        limit: int,
    ) -> DiscoveryTaskListResponse:
        """Return one page of tasks with the total count."""
        total = self._repo.count_tasks(status=status, source=source)
        rows = self._repo.list_tasks_page(Page(offset=offset, limit=limit), status=status, source=source)
        items = [DiscoveryTaskRead.from_row(task, source=task_source) for task, task_source in rows]
        return DiscoveryTaskListResponse(items=items, total=total, offset=offset, limit=limit)

    def list_catalogue(
        self,
        *,
        source: DiscoverySource | None,
        offset: int,
        limit: int,
    ) -> CatalogueListResponse:
        """Return one page of catalogue rows with summary chips."""
        total = self._repo.count_catalogue(source=source)
        rows = self._repo.list_catalogue_page(offset=offset, limit=limit, source=source)
        items = [CatalogueServiceRead.from_row(row) for row in rows]
        return CatalogueListResponse(
            items=items, summary=self._summary(source), total=total, offset=offset, limit=limit
        )

    def coverage(self) -> DiscoveryCoverageResponse:
        """Return coverage counters across sources."""
        counts = self._repo.fetch_coverage_metrics()
        run = counts.last_successful_run
        return DiscoveryCoverageResponse(
            by_source=counts.by_source,
            tasks_pending=counts.task_counts.pending,
            tasks_failed=counts.task_counts.failed,
            emit_ready_count=counts.emit_ready_count,
            task_counts=TaskCountsRead(**asdict(counts.task_counts)),
            fetch_attempts_total=counts.fetch_attempts_total,
            stale_claims=counts.stale_claims,
            stale_runs=counts.stale_runs,
            failures_by_source=counts.failures_by_source,
            last_successful_run=DiscoveryRunRead.model_validate(run) if run is not None else None,
        )

    def emit_preview(self, catalogue_id: UUID) -> EmitPreviewResponse:
        """Preview the suggestions an emit would create."""
        row = require_catalogue(self._repo, catalogue_id)
        entities_by_id = {e.id: e for e in self._repo.list_catalogue_entities(catalogue_id)}
        preview_rows = build_emit_preview_items(
            claims=self._repo.list_catalogue_claims(catalogue_id),
            entities_by_id=entities_by_id,
            jurisdiction_id=row.jurisdiction_id,
        )
        return EmitPreviewResponse(items=[EmitPreviewItemRead.model_validate(i) for i in preview_rows])

    def catalogue_pipeline(self, catalogue_id: UUID) -> CataloguePipelineResponse:
        """Return the read-only pipeline aggregate for one catalogue row."""
        row = require_catalogue(self._repo, catalogue_id)
        task_rows = self._repo.list_catalogue_tasks(catalogue_id)
        fetch_logs = self._repo.list_catalogue_fetch_logs(catalogue_id)
        claims = self._repo.list_catalogue_claims(catalogue_id)
        return CataloguePipelineResponse(
            service=CatalogueServiceRead.from_row(row),
            derived_stage=stage_of(len(task_rows), fetch_logs, claims),
            tasks=[DiscoveryTaskRead.from_row(task, source=source) for task, source in task_rows],
            fetch_logs=[fetch_log_dict(log) for log in fetch_logs],
            entities=[entity_dict(e) for e in self._repo.list_catalogue_entities(catalogue_id)],
            claims=[claim_dict(claim) for claim in claims],
            events=[event_dict(e) for e in self._repo.list_catalogue_events(catalogue_id)],
        )

    def _summary(self, source: DiscoverySource | None) -> CatalogueSummaryChips:
        total, by_source, by_stage = self._repo.catalogue_summary(source=source)
        return CatalogueSummaryChips(total=total, by_source=by_source, by_pipeline_stage=by_stage)
