"""Coverage metrics for the admin catalogue index."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import ColumnElement, func, select

from app.features.discovery.pipeline import PipelineStage
from app.features.discovery.repository.base import SessionRepository
from app.models.base import Base
from app.models.discovery import CatalogueService, DiscoveryTask, DiscoveryTaskStatus


@dataclass(frozen=True, slots=True)
class DiscoveryCoverageCounts:
    """Aggregate coverage metrics for the admin catalogue index."""

    by_source: dict[str, int]
    tasks_pending: int
    tasks_failed: int
    emit_ready_count: int


class CoverageRepository(SessionRepository):
    """Count catalogue rows and tasks for the coverage endpoint."""

    def fetch_coverage_metrics(self) -> DiscoveryCoverageCounts:
        """Return catalogue and task counts for the admin coverage endpoint."""
        return DiscoveryCoverageCounts(
            by_source=self._catalogue_counts_by_source(),
            tasks_pending=self._count_where(DiscoveryTask, DiscoveryTask.status == DiscoveryTaskStatus.PENDING),
            tasks_failed=self._count_where(DiscoveryTask, DiscoveryTask.status == DiscoveryTaskStatus.FAILED),
            emit_ready_count=self._count_where(
                CatalogueService, CatalogueService.pipeline_stage == PipelineStage.T4.value
            ),
        )

    def _catalogue_counts_by_source(self) -> dict[str, int]:
        stmt = select(CatalogueService.source, func.count()).group_by(CatalogueService.source)
        return {str(row[0].value): int(row[1]) for row in self._session.execute(stmt).all()}

    def _count_where(self, model: type[Base], condition: ColumnElement[bool]) -> int:
        stmt = select(func.count()).select_from(model).where(condition)
        return int(self._session.scalar(stmt) or 0)
