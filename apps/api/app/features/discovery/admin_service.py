"""Read-only discovery admin queries for allowlisted operators."""

from __future__ import annotations

from dataclasses import asdict
from uuid import UUID

from app.config import settings
from app.features.discovery.emit_preview import build_emit_preview_items
from app.features.discovery.lookups import require_catalogue
from app.features.discovery.pipeline_rows import (
    claim_dict,
    entity_dict,
    event_dict,
    fetch_log_dict,
    stage_of,
)
from app.features.discovery.repository import (
    CatalogueFilter,
    DiscoveryRepository,
    Page,
    TaskFilter,
    TaskStatusCounts,
)
from app.features.discovery.repository.coverage import DiscoveryCoverageCounts
from app.schema.discovery.read import (
    ArtifactCoverageRead,
    ArtifactTotalsRead,
    CandidateCountsRead,
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
    LlmOutcomesRead,
    TaskCountsRead,
)


def _task_counts_read(counts: TaskStatusCounts) -> TaskCountsRead:
    return TaskCountsRead(**asdict(counts))


def _artifact_coverage(counts: DiscoveryCoverageCounts) -> ArtifactCoverageRead:
    return ArtifactCoverageRead(
        by_kind={kind.value: ArtifactTotalsRead(**asdict(totals)) for kind, totals in counts.artifacts.items()},
        total_bytes=sum(totals.bytes for totals in counts.artifacts.values()),
        bytes_cap=settings.object_store_max_bytes,
    )


class DiscoveryAdminService:
    """Read-only discovery data for allowlisted operators."""

    def __init__(self, repository: DiscoveryRepository) -> None:
        """Bind the service to ``repository``."""
        self._repo = repository

    def list_tasks(self, task_filter: TaskFilter, page: Page) -> DiscoveryTaskListResponse:
        """Return one page of tasks matching ``task_filter`` with the total count."""
        total = self._repo.count_tasks(task_filter)
        rows = self._repo.list_tasks_page(page, task_filter)
        items = [DiscoveryTaskRead.from_row(task, source=task_source) for task, task_source in rows]
        return DiscoveryTaskListResponse(items=items, total=total, offset=page.offset, limit=page.limit)

    def list_catalogue(self, catalogue_filter: CatalogueFilter, page: Page) -> CatalogueListResponse:
        """Return one page of catalogue rows matching ``catalogue_filter`` with the summary chips of the whole catalogue."""
        total = self._repo.count_catalogue(catalogue_filter)
        rows = self._repo.list_catalogue_page(offset=page.offset, limit=page.limit, catalogue_filter=catalogue_filter)
        items = [CatalogueServiceRead.from_row(row) for row in rows]
        return CatalogueListResponse(
            items=items, summary=self._summary(), total=total, offset=page.offset, limit=page.limit
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
            task_counts=_task_counts_read(counts.task_counts),
            task_counts_by_kind={kind.value: _task_counts_read(c) for kind, c in counts.task_counts_by_kind.items()},
            candidates=CandidateCountsRead(**asdict(counts.candidates)),
            llm_outcomes=LlmOutcomesRead(**asdict(counts.llm_outcomes)),
            artifacts=_artifact_coverage(counts),
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

    def _summary(self) -> CatalogueSummaryChips:
        """Return the chips of the whole catalogue, so filter chips stay switchable while a filter is active."""
        total, by_source, by_stage = self._repo.catalogue_summary()
        return CatalogueSummaryChips(total=total, by_source=by_source, by_pipeline_stage=by_stage)
