"""Idempotent discovery task enqueue helpers."""

from __future__ import annotations

from app.features.discovery.repository import DiscoveryRepository, NewEvent, TaskTarget
from app.models.discovery import DiscoveryEventType, DiscoveryTask, DiscoveryTaskStatus

_SKIP_REENQUEUE_STATUSES = (
    DiscoveryTaskStatus.PENDING,
    DiscoveryTaskStatus.CLAIMED,
    DiscoveryTaskStatus.COMPLETED,
)


def enqueue_task_if_needed(
    repo: DiscoveryRepository,
    target: TaskTarget,
    *,
    priority: int = 100,
) -> DiscoveryTask | None:
    """Insert a pending task unless an equivalent open or completed task already exists."""

    existing = repo.find_task_for_target(target, statuses=_SKIP_REENQUEUE_STATUSES)
    if existing is not None:
        return existing
    task = repo.insert_task(target, priority=priority)
    repo.record_event(
        NewEvent(
            event_type=DiscoveryEventType.TASK_ENQUEUED,
            catalogue_service_id=target.catalogue_service_id,
            discovery_task_id=task.id,
            payload={"kind": task.kind.value, "target_url": task.target_url},
        )
    )
    return task
