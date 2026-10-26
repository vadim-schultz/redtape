"""Lease and claim bookkeeping shared by every way a claimed task leaves the worker."""

from __future__ import annotations

from datetime import datetime

from app.models.discovery import DiscoveryTask, DiscoveryTaskStatus


def clear_lease(task: DiscoveryTask) -> None:
    """End the task's lease."""
    task.lease_expires_at = None


def clear_claim(task: DiscoveryTask) -> None:
    """Forget which key claimed the task and when, as after a hand-back to the queue."""
    task.claimed_at = None
    task.claimed_by_api_key_id = None


def hand_back(task: DiscoveryTask, reason: str, not_before: datetime | None) -> None:
    """Return a claimed task to ``pending`` and give back the attempt its claim consumed (never below zero)."""
    task.status = DiscoveryTaskStatus.PENDING
    task.attempt_count = max(task.attempt_count - 1, 0)
    task.last_error = reason
    task.not_before = not_before or task.not_before
    clear_lease(task)
    clear_claim(task)
