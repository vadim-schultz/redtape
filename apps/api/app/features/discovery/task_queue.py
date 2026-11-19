"""Crawler task queue: enqueue on upsert, lease on claim, finish or fail."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from app.features.discovery.errors import TaskNotClaimedError
from app.features.discovery.lookups import require_task
from app.features.discovery.repository import DiscoveryRepository, NewEvent, TaskTarget
from app.features.discovery.stage_sync import advance_stage
from app.features.discovery.task_enqueue import EnqueueOutcome, enqueue_task_if_needed, enqueue_task_with_outcome
from app.features.discovery.task_lease import clear_lease, hand_back, lease
from app.features.discovery.task_retry import MAX_ATTEMPTS, TRANSIENT_COOLDOWN, settle_failure
from app.models.api_key import ApiKey
from app.models.discovery import (
    LEGACY_TASK_KINDS,
    CatalogueService,
    DiscoveryEventType,
    DiscoveryFailureClass,
    DiscoveryTask,
    DiscoveryTaskKind,
    DiscoveryTaskStatus,
)


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
        advance_stage(self._repo, service)
        return task

    def enqueue(self, target: TaskTarget, *, priority: int = 100) -> EnqueueOutcome:
        """Enqueue ``target`` unless an equivalent task exists; report whether it was created."""
        return enqueue_task_with_outcome(self._repo, target, priority=priority)

    def claim_pending(
        self,
        *,
        api_key: ApiKey,
        limit: int,
        now: datetime,
        kinds: Sequence[DiscoveryTaskKind] = LEGACY_TASK_KINDS,
    ) -> list[DiscoveryTask]:
        """Reclaim expired leases, then lease up to ``limit`` pending ``kinds`` tasks to ``api_key``."""
        self._repo.reclaim_expired_claims(now=now, max_attempts=MAX_ATTEMPTS)
        pending = self._repo.list_pending_tasks_for_claim(limit=limit, kinds=kinds, now=now)
        return [self._lease(task, api_key, now) for task in pending]

    def complete(self, task_id: UUID, note: str | None = None, *, text_hash: str | None = None) -> DiscoveryTask:
        """Mark a task completed, release its lease, and keep the optional ``note`` and the ``text_hash`` it read."""
        task = require_task(self._repo, task_id)
        task.status = DiscoveryTaskStatus.COMPLETED
        task.result_note = note
        task.text_hash = text_hash
        clear_lease(task)
        return task

    def release(self, task_id: UUID, reason: str, *, not_before: datetime | None = None) -> DiscoveryTask:
        """Hand a claimed task back to ``pending`` and give back the attempt its claim consumed.

        A limit (quota, storage) stopped the work, not the page, so the claim must not count towards
        ``MAX_ATTEMPTS``. ``reason`` becomes ``last_error``; ``not_before`` holds the task back when given.
        """
        task = require_task(self._repo, task_id)
        if task.status is not DiscoveryTaskStatus.CLAIMED:
            raise TaskNotClaimedError()
        hand_back(task, reason, not_before)
        self._repo.record_event(_released_event(task, reason))
        return task

    def fail(
        self,
        task_id: UUID,
        error: str,
        *,
        retryable: bool = False,
        now: datetime,
        failure_class: DiscoveryFailureClass | None = None,
    ) -> DiscoveryTask:
        """Record ``error`` and its ``failure_class`` on a task: re-pend it with backoff if retryable and under the cap, else fail it."""
        task = require_task(self._repo, task_id)
        settle_failure(task, error, retryable=retryable, now=now, failure_class=failure_class)
        return task

    def requeue_transient(self, *, limit: int, now: datetime) -> int:
        """Return up to ``limit`` transient failures that are at least the cooldown old to pending; return how many."""
        return self._repo.requeue_transient(cutoff=now - TRANSIENT_COOLDOWN, limit=limit)

    def _lease(self, task: DiscoveryTask, api_key: ApiKey, now: datetime) -> DiscoveryTask:
        task.status = DiscoveryTaskStatus.CLAIMED
        lease(task, api_key.id, now)
        task.attempt_count += 1
        self._repo.record_event(_claimed_event(task, api_key))
        return task


def _claimed_event(task: DiscoveryTask, api_key: ApiKey) -> NewEvent:
    return NewEvent(
        event_type=DiscoveryEventType.TASK_CLAIMED,
        catalogue_service_id=task.catalogue_service_id,
        discovery_task_id=task.id,
        payload={"api_key_id": str(api_key.id)},
    )


def _released_event(task: DiscoveryTask, reason: str) -> NewEvent:
    return NewEvent(
        event_type=DiscoveryEventType.TASK_RELEASED,
        catalogue_service_id=task.catalogue_service_id,
        discovery_task_id=task.id,
        payload={"reason": reason},
    )
