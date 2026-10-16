"""Idempotent discovery task enqueue helpers."""

from __future__ import annotations

from uuid import UUID

from app.features.discovery.repository import DiscoveryRepository
from app.models.discovery import DiscoveryEventType, DiscoveryTask, DiscoveryTaskKind, DiscoveryTaskStatus

_SKIP_REENQUEUE_STATUSES = (
    DiscoveryTaskStatus.PENDING,
    DiscoveryTaskStatus.CLAIMED,
    DiscoveryTaskStatus.COMPLETED,
)


def enqueue_task_if_needed(
    repo: DiscoveryRepository,
    *,
    catalogue_service_id: UUID,
    kind: DiscoveryTaskKind,
    target_url: str,
    priority: int = 100,
) -> DiscoveryTask | None:
    """Insert a pending task unless an equivalent open or completed task already exists."""

    existing = repo.find_task_for_target(
        catalogue_service_id=catalogue_service_id,
        kind=kind,
        target_url=target_url,
        statuses=_SKIP_REENQUEUE_STATUSES,
    )
    if existing is not None:
        return existing
    task = repo.insert_task(
        catalogue_service_id=catalogue_service_id,
        kind=kind,
        target_url=target_url,
        priority=priority,
    )
    repo.record_event(
        event_type=DiscoveryEventType.TASK_ENQUEUED,
        catalogue_service_id=catalogue_service_id,
        discovery_task_id=task.id,
        payload={"kind": task.kind.value, "target_url": task.target_url},
    )
    return task
