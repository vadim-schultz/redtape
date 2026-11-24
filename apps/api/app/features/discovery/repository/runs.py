"""Operational run persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import ColumnElement, func, select, update

from app.features.discovery.repository.base import SessionRepository
from app.models.discovery import DiscoveryRun, DiscoveryRunKind, DiscoveryRunStage, DiscoveryRunStatus

STALE_RUN_AFTER = timedelta(hours=1)
STALE_RUN_DETAIL = "stale: no finish received"


@dataclass(frozen=True, slots=True)
class RunReport:
    """Final counts and stop reason recorded when a run closes."""

    status: DiscoveryRunStatus
    claimed_count: int
    completed_count: int
    failed_count: int
    skipped_count: int
    remaining_count: int | None
    stop_reason: str | None
    error_detail: str | None
    spend: dict[str, float] | None = None


class RunRepository(SessionRepository):
    """Read and write operational run records."""

    def insert_run(self, kind: DiscoveryRunKind, stage: DiscoveryRunStage, *, started_at: datetime) -> DiscoveryRun:
        """Insert a ``running`` run of ``kind`` for ``stage``."""
        run = DiscoveryRun(
            kind=kind.value, stage=stage.value, status=DiscoveryRunStatus.RUNNING.value, started_at=started_at
        )
        self._session.add(run)
        self._session.flush()
        return run

    def get_run(self, run_id: UUID) -> DiscoveryRun | None:
        """Return the run with ``run_id``, if any."""
        return self._session.get(DiscoveryRun, run_id)

    def close_run(self, run: DiscoveryRun, report: RunReport, *, finished_at: datetime) -> DiscoveryRun:
        """Store ``report`` on ``run`` and mark it finished."""
        run.status = report.status.value
        run.finished_at = finished_at
        run.claimed_count = report.claimed_count
        run.completed_count = report.completed_count
        run.failed_count = report.failed_count
        run.skipped_count = report.skipped_count
        run.remaining_count = report.remaining_count
        run.stop_reason = report.stop_reason
        run.error_detail = report.error_detail
        run.spend = report.spend
        self._session.flush()
        return run

    def latest_successful_run(self) -> DiscoveryRun | None:
        """Return the most recently finished ``succeeded`` run, if any."""
        stmt = (
            select(DiscoveryRun)
            .where(DiscoveryRun.status == DiscoveryRunStatus.SUCCEEDED.value)
            .order_by(DiscoveryRun.finished_at.desc())
            .limit(1)
        )
        return self._session.scalar(stmt)

    def count_stale_runs(self, *, now: datetime) -> int:
        """Return ``running`` runs started before ``now`` minus the stale window."""
        stmt = select(func.count()).select_from(DiscoveryRun).where(*_stale(now))
        return int(self._session.scalar(stmt) or 0)

    def close_stale_runs(self, *, now: datetime) -> None:
        """Close every stale ``running`` run as failed, with the stale reason."""
        stmt = (
            update(DiscoveryRun)
            .where(*_stale(now))
            .values(
                status=DiscoveryRunStatus.FAILED.value,
                finished_at=now,
                stop_reason="error",
                error_detail=STALE_RUN_DETAIL,
            )
        )
        self._session.execute(stmt)


def _stale(now: datetime) -> tuple[ColumnElement[bool], ...]:
    """Return the predicates that make a run stale at ``now``: still running and started before the stale window."""
    return (
        DiscoveryRun.status == DiscoveryRunStatus.RUNNING.value,
        DiscoveryRun.started_at < now - STALE_RUN_AFTER,
    )
