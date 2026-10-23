"""Queue, fetch, lease, and per-source failure aggregates."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select

from app.features.discovery.repository.base import SessionRepository
from app.models.discovery import CatalogueService, DiscoveryFetchLog, DiscoveryTask, DiscoveryTaskStatus


@dataclass(frozen=True, slots=True)
class TaskStatusCounts:
    """Task totals grouped by current status."""

    total: int
    pending: int
    claimed: int
    completed: int
    failed: int


class QueueMetricsRepository(SessionRepository):
    """Aggregate the durable queue state for operators."""

    def task_status_counts(self) -> TaskStatusCounts:
        """Return the total task count and the count per status."""
        stmt = select(DiscoveryTask.status, func.count()).group_by(DiscoveryTask.status)
        by_status = {row[0]: int(row[1]) for row in self._session.execute(stmt).all()}

        def count(status: DiscoveryTaskStatus) -> int:
            return by_status.get(status, 0)

        return TaskStatusCounts(
            total=sum(by_status.values()),
            pending=count(DiscoveryTaskStatus.PENDING),
            claimed=count(DiscoveryTaskStatus.CLAIMED),
            completed=count(DiscoveryTaskStatus.COMPLETED),
            failed=count(DiscoveryTaskStatus.FAILED),
        )

    def count_fetch_attempts(self) -> int:
        """Return the number of append-only fetch log rows."""
        return int(self._session.scalar(select(func.count()).select_from(DiscoveryFetchLog)) or 0)

    def count_stale_claims(self, *, now: datetime) -> int:
        """Return claimed tasks whose lease expired before ``now``."""
        stmt = (
            select(func.count())
            .select_from(DiscoveryTask)
            .where(
                DiscoveryTask.status == DiscoveryTaskStatus.CLAIMED,
                DiscoveryTask.lease_expires_at.is_not(None),
                DiscoveryTask.lease_expires_at < now,
            )
        )
        return int(self._session.scalar(stmt) or 0)

    def failed_counts_by_source(self) -> dict[str, int]:
        """Return failed task counts keyed by catalogue source."""
        stmt = (
            select(CatalogueService.source, func.count())
            .select_from(DiscoveryTask)
            .join(CatalogueService, CatalogueService.id == DiscoveryTask.catalogue_service_id)
            .where(DiscoveryTask.status == DiscoveryTaskStatus.FAILED)
            .group_by(CatalogueService.source)
        )
        return {str(row[0].value): int(row[1]) for row in self._session.execute(stmt).all()}
