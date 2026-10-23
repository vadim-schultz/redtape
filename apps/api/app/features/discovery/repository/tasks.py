"""Discovery task queue queries."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select

from app.features.discovery.repository.base import SessionRepository
from app.features.discovery.repository.task_clauses import claimable, fail_exhausted_stmt, repend_expired_stmt
from app.models.discovery import (
    DiscoveryTask,
    DiscoveryTaskKind,
    DiscoveryTaskStatus,
)

QUEUE_ORDER = (DiscoveryTask.priority.asc(), DiscoveryTask.created_at.asc(), DiscoveryTask.id.asc())


@dataclass(frozen=True, slots=True)
class TaskTarget:
    """Identify a task by catalogue row, kind, target URL and optional input key."""

    catalogue_service_id: UUID
    kind: DiscoveryTaskKind
    target_url: str
    input_key: str | None = None


class TaskRepository(SessionRepository):
    """Read and write the discovery task queue."""

    def find_task_for_target(
        self, target: TaskTarget, *, statuses: tuple[DiscoveryTaskStatus, ...]
    ) -> DiscoveryTask | None:
        """Return a task for ``target`` whose status is one of ``statuses``."""
        stmt = (
            select(DiscoveryTask)
            .where(
                DiscoveryTask.catalogue_service_id == target.catalogue_service_id,
                DiscoveryTask.kind == target.kind,
                DiscoveryTask.target_url == target.target_url,
                DiscoveryTask.input_key == target.input_key,
                DiscoveryTask.status.in_(statuses),
            )
            .limit(1)
        )
        return self._session.scalar(stmt)

    def insert_task(self, target: TaskTarget, *, priority: int = 100) -> DiscoveryTask:
        """Insert a pending task for ``target``."""
        task = DiscoveryTask(
            catalogue_service_id=target.catalogue_service_id,
            kind=target.kind,
            target_url=target.target_url,
            input_key=target.input_key,
            status=DiscoveryTaskStatus.PENDING,
            priority=priority,
        )
        self._session.add(task)
        self._session.flush()
        return task

    def reclaim_expired_claims(self, *, now: datetime, max_attempts: int) -> None:
        """Fail expired leases that used ``max_attempts``; return the rest to the pending queue."""
        self._session.execute(fail_exhausted_stmt(now, max_attempts))
        self._session.execute(repend_expired_stmt(now))
        self._session.flush()

    def list_pending_tasks_for_claim(
        self, *, limit: int, kinds: Sequence[DiscoveryTaskKind], now: datetime
    ) -> list[DiscoveryTask]:
        """Return up to ``limit`` tasks of the given ``kinds`` that are claimable at ``now``, in queue order."""
        stmt = select(DiscoveryTask).where(*claimable(now), DiscoveryTask.kind.in_(kinds))
        return list(self._session.scalars(stmt.order_by(*QUEUE_ORDER).limit(limit)).all())

    def get_task(self, task_id: UUID) -> DiscoveryTask | None:
        """Return the task with ``task_id``, if any."""
        return self._session.get(DiscoveryTask, task_id)
