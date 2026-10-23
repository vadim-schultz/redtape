"""Idempotent discovery task enqueue helpers."""

from __future__ import annotations

from dataclasses import dataclass

from app.features.discovery.repository import DiscoveryRepository, NewEvent, TaskTarget
from app.models.discovery import DiscoveryEventType, DiscoveryTask, DiscoveryTaskStatus

_SKIP_REENQUEUE_STATUSES = (
    DiscoveryTaskStatus.PENDING,
    DiscoveryTaskStatus.CLAIMED,
    DiscoveryTaskStatus.COMPLETED,
)


@dataclass(frozen=True, slots=True)
class EnqueueOutcome:
    """The task behind an enqueue request and whether this call created it."""

    task: DiscoveryTask
    created: bool


def enqueue_task_if_needed(
    repo: DiscoveryRepository,
    target: TaskTarget,
    *,
    priority: int = 100,
) -> DiscoveryTask | None:
    """Insert a pending task unless an equivalent open or completed task already exists."""

    return enqueue_task_with_outcome(repo, target, priority=priority).task


def enqueue_task_with_outcome(
    repo: DiscoveryRepository,
    target: TaskTarget,
    *,
    priority: int = 100,
) -> EnqueueOutcome:
    """Like ``enqueue_task_if_needed`` but report whether a new task was inserted."""

    existing = repo.find_task_for_target(target, statuses=_SKIP_REENQUEUE_STATUSES)
    if existing is not None:
        return EnqueueOutcome(task=existing, created=False)
    task = repo.insert_task(target, priority=priority)
    repo.record_event(
        NewEvent(
            event_type=DiscoveryEventType.TASK_ENQUEUED,
            catalogue_service_id=target.catalogue_service_id,
            discovery_task_id=task.id,
            payload={"kind": task.kind.value, "target_url": task.target_url},
        )
    )
    return EnqueueOutcome(task=task, created=True)
