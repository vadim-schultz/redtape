"""Lease and claim bookkeeping shared by every way a claimed task leaves the worker."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Final, Protocol
from uuid import UUID

from app.models.discovery import DiscoveryTask, DiscoveryTaskStatus

TASK_LEASE_MINUTES: Final = 15
"""How long a claim holds a task before another claimer may reclaim it; every leased queue uses this one value."""
LEASE_DURATION: Final = timedelta(minutes=TASK_LEASE_MINUTES)


class LeaseFields(Protocol):
    """The columns every leased task row carries, whichever table it lives in."""

    claimed_at: datetime | None
    claimed_by_api_key_id: UUID | None
    lease_expires_at: datetime | None


def lease(task: LeaseFields, api_key_id: UUID, now: datetime) -> None:
    """Record that ``api_key_id`` claimed ``task`` at ``now`` and holds it for :data:`LEASE_DURATION`."""
    task.claimed_at = now
    task.claimed_by_api_key_id = api_key_id
    task.lease_expires_at = now + LEASE_DURATION


def clear_lease(task: LeaseFields) -> None:
    """End the task's lease."""
    task.lease_expires_at = None


def clear_claim(task: LeaseFields) -> None:
    """Forget which key claimed the task and when, as after a hand-back to the queue."""
    task.claimed_at = None
    task.claimed_by_api_key_id = None


def attempts_after_hand_back(attempt_count: int) -> int:
    """Return the attempts left after a hand-back gives back the one its claim consumed (never below zero)."""
    return max(attempt_count - 1, 0)


def hand_back(task: DiscoveryTask, reason: str, not_before: datetime | None) -> None:
    """Return a claimed task to ``pending`` and give back the attempt its claim consumed (never below zero)."""
    task.status = DiscoveryTaskStatus.PENDING
    task.attempt_count = attempts_after_hand_back(task.attempt_count)
    task.last_error = reason
    task.not_before = not_before or task.not_before
    clear_lease(task)
    clear_claim(task)
