"""Coverage metrics for the admin catalogue index."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import ColumnElement, func, select

from app.features.discovery.pipeline import PipelineStage
from app.features.discovery.repository.artifacts import ArtifactRepository, ArtifactTotals
from app.features.discovery.repository.queue_metrics import QueueMetricsRepository, TaskStatusCounts
from app.features.discovery.repository.runs import RunRepository
from app.models.base import Base
from app.models.discovery import (
    CatalogueService,
    DiscoveryArtifactKind,
    DiscoveryCandidateMention,
    DiscoveryCandidateStatus,
    DiscoveryDocumentCandidate,
    DiscoveryRun,
    DiscoveryTaskKind,
)


@dataclass(frozen=True, slots=True)
class CandidateCounts:
    """Document candidate totals by lifecycle status, plus the mentions that evidence them."""

    total: int
    staged: int
    emitted: int
    mentions: int


@dataclass(frozen=True, slots=True)
class DiscoveryCoverageCounts:
    """Aggregate coverage and queue metrics for the admin coverage surface."""

    by_source: dict[str, int]
    emit_ready_count: int
    task_counts: TaskStatusCounts
    task_counts_by_kind: dict[DiscoveryTaskKind, TaskStatusCounts]
    candidates: CandidateCounts
    artifacts: dict[DiscoveryArtifactKind, ArtifactTotals]
    fetch_attempts_total: int
    stale_claims: int
    stale_runs: int
    failures_by_source: dict[str, int]
    last_successful_run: DiscoveryRun | None


class CoverageRepository(QueueMetricsRepository, RunRepository, ArtifactRepository):
    """Count catalogue rows, tasks, fetches, and runs for the coverage endpoint."""

    def fetch_coverage_metrics(self) -> DiscoveryCoverageCounts:
        """Return catalogue, queue, and run metrics for the admin coverage endpoint."""
        now = datetime.now(UTC)
        return DiscoveryCoverageCounts(
            by_source=self._catalogue_counts_by_source(),
            emit_ready_count=self._count_where(
                CatalogueService, CatalogueService.pipeline_stage == PipelineStage.T4.value
            ),
            task_counts=self.task_status_counts(),
            task_counts_by_kind=self.task_counts_by_kind(),
            candidates=self._candidate_counts(),
            artifacts=self.artifact_totals(),
            fetch_attempts_total=self.count_fetch_attempts(),
            stale_claims=self.count_stale_claims(now=now),
            stale_runs=self.count_stale_runs(now=now),
            failures_by_source=self.failed_counts_by_source(),
            last_successful_run=self.latest_successful_run(),
        )

    def _catalogue_counts_by_source(self) -> dict[str, int]:
        stmt = select(CatalogueService.source, func.count()).group_by(CatalogueService.source)
        return {str(row[0].value): int(row[1]) for row in self._session.execute(stmt).all()}

    def _candidate_counts(self) -> CandidateCounts:
        stmt = select(DiscoveryDocumentCandidate.status, func.count()).group_by(DiscoveryDocumentCandidate.status)
        by_status = {row[0]: int(row[1]) for row in self._session.execute(stmt).all()}
        return CandidateCounts(
            total=sum(by_status.values()),
            staged=by_status.get(DiscoveryCandidateStatus.STAGED, 0),
            emitted=by_status.get(DiscoveryCandidateStatus.EMITTED, 0),
            mentions=int(self._session.scalar(select(func.count()).select_from(DiscoveryCandidateMention)) or 0),
        )

    def _count_where(self, model: type[Base], condition: ColumnElement[bool]) -> int:
        stmt = select(func.count()).select_from(model).where(condition)
        return int(self._session.scalar(stmt) or 0)
