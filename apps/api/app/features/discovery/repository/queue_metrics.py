"""Queue, fetch, lease, and per-source failure aggregates."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import ColumnElement, Row, func, select

from app.features.discovery.repository.base import SessionRepository
from app.features.discovery.repository.task_clauses import claimable, delayed, expired_lease
from app.models.discovery import (
    CatalogueService,
    DiscoveryFetchLog,
    DiscoveryTask,
    DiscoveryTaskKind,
    DiscoveryTaskStatus,
)
from app.shared.queue_stats import age_seconds, finished_recently, oldest_ready


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
    """Queue counts for a set of task kinds; ``claimed`` includes the ``claimed_stale`` leases.

    ``oldest_pending_age_seconds`` is the age of the oldest ready task (``None`` when none is ready); the 24 h counts
    are the tasks completed or failed within the last day.
    """

    pending_ready: int
    pending_delayed: int
    claimed: int
    claimed_stale: int
    completed: int
    failed: int
    oldest_pending_age_seconds: float | None = None
    completed_24h: int = 0
    failed_24h: int = 0


def _status_counts(tally: Counter[DiscoveryTaskStatus]) -> TaskStatusCounts:
    return TaskStatusCounts(
        total=tally.total(),
        pending=tally[DiscoveryTaskStatus.PENDING],
        claimed=tally[DiscoveryTaskStatus.CLAIMED],
        completed=tally[DiscoveryTaskStatus.COMPLETED],
        failed=tally[DiscoveryTaskStatus.FAILED],
    )


def _status(status: DiscoveryTaskStatus) -> tuple[ColumnElement[bool], ...]:
    return (DiscoveryTask.status == status,)


class QueueMetricsRepository(SessionRepository):
    """Aggregate the durable queue state for operators."""

    def task_status_counts(self) -> TaskStatusCounts:
        """Return the total task count and the count per status, across every kind."""
        overall: Counter[DiscoveryTaskStatus] = Counter()
        for tally in self._status_tallies().values():
            overall.update(tally)
        return _status_counts(overall)

    def task_counts_by_kind(self) -> dict[DiscoveryTaskKind, TaskStatusCounts]:
        """Return the total and per-status task counts of every kind, including kinds without tasks."""
        return {kind: _status_counts(tally) for kind, tally in self._status_tallies().items()}

    def _status_tallies(self) -> dict[DiscoveryTaskKind, Counter[DiscoveryTaskStatus]]:
        stmt = select(DiscoveryTask.kind, DiscoveryTask.status, func.count()).group_by(
            DiscoveryTask.kind, DiscoveryTask.status
        )
        tallies = {kind: Counter[DiscoveryTaskStatus]() for kind in DiscoveryTaskKind}
        for kind, status, count in self._session.execute(stmt).all():
            tallies[kind][status] = int(count)
        return tallies

    def task_summary(self, *, kinds: Sequence[DiscoveryTaskKind], now: datetime) -> TaskSummary:
        """Return one grouped count of ``kinds`` tasks at ``now`` without leasing or mutating anything."""
        counts = [func.count().filter(*clauses) for clauses in _summary_clauses(now)]
        oldest = oldest_ready(DiscoveryTask.created_at, claimable(now))
        completed = finished_recently(
            DiscoveryTask.status == DiscoveryTaskStatus.COMPLETED, DiscoveryTask.updated_at, now
        )
        failed = finished_recently(DiscoveryTask.status == DiscoveryTaskStatus.FAILED, DiscoveryTask.updated_at, now)
        stmt = select(*counts, oldest, completed, failed).where(DiscoveryTask.kind.in_(kinds))
        return _task_summary(self._session.execute(stmt).one(), now)

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


def _task_summary(
    row: Row[tuple[int, int, int, int, int, int, datetime | None, int, int]], now: datetime
) -> TaskSummary:
    """Map one summary row: the six counts, the oldest ready creation time, then the 24 h completed and failed counts."""
    pending_ready, pending_delayed, claimed, claimed_stale, done, broke, oldest, completed, failed = row
    return TaskSummary(
        pending_ready=pending_ready,
        pending_delayed=pending_delayed,
        claimed=claimed,
        claimed_stale=claimed_stale,
        completed=done,
        failed=broke,
        oldest_pending_age_seconds=age_seconds(oldest, now),
        completed_24h=completed,
        failed_24h=failed,
    )


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
