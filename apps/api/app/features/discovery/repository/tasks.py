"""Discovery task queue queries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import Update, select, update

from app.features.discovery.repository.base import SessionRepository
from app.models.discovery import (
    DiscoveryTask,
    DiscoveryTaskKind,
    DiscoveryTaskStatus,
)

QUEUE_ORDER = (DiscoveryTask.priority.asc(), DiscoveryTask.created_at.asc(), DiscoveryTask.id.asc())


@dataclass(frozen=True, slots=True)
class TaskTarget:
    """Identify a task by catalogue row, kind and target URL."""

    catalogue_service_id: UUID
    kind: DiscoveryTaskKind
    target_url: str


def _reclaim_expired_stmt(now: datetime) -> Update:
    return (
        update(DiscoveryTask)
        .where(
            DiscoveryTask.status == DiscoveryTaskStatus.CLAIMED,
            DiscoveryTask.lease_expires_at.is_not(None),
            DiscoveryTask.lease_expires_at < now,
        )
        .values(
            status=DiscoveryTaskStatus.PENDING,
            claimed_by_api_key_id=None,
            claimed_at=None,
            lease_expires_at=None,
        )
    )


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
            status=DiscoveryTaskStatus.PENDING,
            priority=priority,
        )
        self._session.add(task)
        self._session.flush()
        return task

    def reclaim_expired_claims(self, *, now: datetime) -> None:
        """Return claimed tasks with expired leases to the pending queue."""
        self._session.execute(_reclaim_expired_stmt(now))
        self._session.flush()

    def list_pending_tasks_for_claim(self, *, limit: int) -> list[DiscoveryTask]:
        """Return up to ``limit`` pending tasks in queue order."""
        stmt = select(DiscoveryTask).where(DiscoveryTask.status == DiscoveryTaskStatus.PENDING)
        return list(self._session.scalars(stmt.order_by(*QUEUE_ORDER).limit(limit)).all())

    def get_task(self, task_id: UUID) -> DiscoveryTask | None:
        """Return the task with ``task_id``, if any."""
        return self._session.get(DiscoveryTask, task_id)
