"""Crawler task queue: enqueue on upsert, lease on claim, finish or fail."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from app.features.discovery.lookups import require_task
from app.features.discovery.repository import DiscoveryRepository, NewEvent, TaskTarget
from app.features.discovery.stage_sync import advance_stage
from app.features.discovery.task_enqueue import enqueue_task_if_needed
from app.models.api_key import ApiKey
from app.models.discovery import (
    CatalogueService,
    DiscoveryEventType,
    DiscoveryTask,
    DiscoveryTaskKind,
    DiscoveryTaskStatus,
)

TASK_LEASE_MINUTES = 15


class TaskQueue:
    """Mutations on discovery tasks."""

    def __init__(self, repository: DiscoveryRepository) -> None:
        """Bind the queue to ``repository``."""
        self._repo = repository

    def enqueue_for_service(self, service: CatalogueService) -> DiscoveryTask | None:
        """Enqueue the portal fetch task for ``service`` and advance its stage."""
        if not service.portal_url:
            return None
        target = TaskTarget(
            catalogue_service_id=service.id,
            kind=DiscoveryTaskKind.FETCH_URL,
            target_url=service.portal_url,
        )
        task = enqueue_task_if_needed(self._repo, target)
        if task is not None:
            advance_stage(self._repo, service)
        return task

    def claim_pending(self, *, api_key: ApiKey, limit: int, now: datetime) -> list[DiscoveryTask]:
        """Reclaim expired leases, then lease up to ``limit`` pending tasks to ``api_key``."""
        self._repo.reclaim_expired_claims(now=now)
        pending = self._repo.list_pending_tasks_for_claim(limit=limit)
        return [self._lease(task, api_key, now) for task in pending]

    def complete(self, task_id: UUID) -> DiscoveryTask:
        """Mark a task completed and release its lease."""
        task = require_task(self._repo, task_id)
        task.status = DiscoveryTaskStatus.COMPLETED
        task.lease_expires_at = None
        return task

    def fail(self, task_id: UUID, error: str) -> DiscoveryTask:
        """Mark a task failed with ``error`` and release its lease."""
        task = require_task(self._repo, task_id)
        task.status = DiscoveryTaskStatus.FAILED
        task.last_error = error
        task.lease_expires_at = None
        return task

    def _lease(self, task: DiscoveryTask, api_key: ApiKey, now: datetime) -> DiscoveryTask:
        task.status = DiscoveryTaskStatus.CLAIMED
        task.claimed_at = now
        task.claimed_by_api_key_id = api_key.id
        task.lease_expires_at = now + timedelta(minutes=TASK_LEASE_MINUTES)
        self._repo.record_event(_claimed_event(task, api_key))
        return task


def _claimed_event(task: DiscoveryTask, api_key: ApiKey) -> NewEvent:
    return NewEvent(
        event_type=DiscoveryEventType.TASK_CLAIMED,
        catalogue_service_id=task.catalogue_service_id,
        discovery_task_id=task.id,
        payload={"api_key_id": str(api_key.id)},
    )
