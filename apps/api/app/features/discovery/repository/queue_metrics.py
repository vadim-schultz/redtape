"""Queue, fetch, lease, and per-source failure aggregates."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import ColumnElement, func, select

from app.features.discovery.repository.base import SessionRepository
from app.features.discovery.repository.task_clauses import claimable, delayed, expired_lease
from app.models.discovery import (
    CatalogueService,
    DiscoveryFetchLog,
    DiscoveryTask,
    DiscoveryTaskKind,
    DiscoveryTaskStatus,
)


@dataclass(frozen=True, slots=True)
class TaskStatusCounts:
    """Task totals grouped by current status."""

    total: int
    pending: int
    claimed: int
    completed: int
    failed: int


@dataclass(frozen=True, slots=True)
class TaskSummary:
    """Queue counts for a set of task kinds; ``claimed`` includes the ``claimed_stale`` leases."""

    pending_ready: int
    pending_delayed: int
    claimed: int
    claimed_stale: int
    completed: int
    failed: int


def _status(status: DiscoveryTaskStatus) -> tuple[ColumnElement[bool], ...]:
    return (DiscoveryTask.status == status,)


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

    def task_summary(self, *, kinds: Sequence[DiscoveryTaskKind], now: datetime) -> TaskSummary:
        """Return one grouped count of ``kinds`` tasks at ``now`` without leasing or mutating anything."""
        columns = [func.count().filter(*clauses) for clauses in _summary_clauses(now)]
        row = self._session.execute(select(*columns).where(DiscoveryTask.kind.in_(kinds))).one()
        return TaskSummary(*(int(value) for value in row))

    def count_fetch_attempts(self) -> int:
        """Return the number of append-only fetch log rows."""
        return int(self._session.scalar(select(func.count()).select_from(DiscoveryFetchLog)) or 0)

    def count_stale_claims(self, *, now: datetime) -> int:
        """Return claimed tasks whose lease expired before ``now``."""
        stmt = select(func.count()).select_from(DiscoveryTask).where(*expired_lease(now))
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


def _summary_clauses(now: datetime) -> tuple[tuple[ColumnElement[bool], ...], ...]:
    """Return the filter for each :class:`TaskSummary` field, in field order."""
    return (
        claimable(now),
        delayed(now),
        _status(DiscoveryTaskStatus.CLAIMED),
        expired_lease(now),
        _status(DiscoveryTaskStatus.COMPLETED),
        _status(DiscoveryTaskStatus.FAILED),
    )
