"""How a leased work task enters and leaves the claimed state, on any work-task table."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.features.discovery.task_lease import LeaseFields, attempts_after_hand_back, clear_claim, clear_lease, lease
from app.features.discovery.task_retry import FailureKind, RetryFields, apply_retry_policy
from app.features.search.task_states import HasStatus, move
from app.models.search import WorkTaskStatus


class WorkTaskFields(HasStatus, RetryFields, LeaseFields, Protocol):
    """The columns the settle steps touch; every work-task table has them."""


def lease_task(task: WorkTaskFields, api_key_id: UUID, now: datetime) -> None:
    """Claim ``task`` for ``api_key_id``: lease it and count the attempt."""
    move(task, WorkTaskStatus.CLAIMED)
    lease(task, api_key_id, now)
    task.attempt_count += 1


def complete_task(task: WorkTaskFields) -> None:
    """Finish ``task`` and end its lease."""
    move(task, WorkTaskStatus.COMPLETED)
    clear_lease(task)


def fail_task(task: WorkTaskFields, error: str, kind: FailureKind, now: datetime) -> None:
    """Record ``error``; a retryable failure under the attempt cap re-pends with backoff, any other fails the task."""
    repended = apply_retry_policy(task, error, kind, now)
    move(task, WorkTaskStatus.PENDING if repended else WorkTaskStatus.FAILED)


def release_task(task: WorkTaskFields, reason: str) -> None:
    """Hand ``task`` back to ``pending`` and give back the attempt its claim consumed, keeping ``reason``."""
    move(task, WorkTaskStatus.PENDING)
    task.attempt_count = attempts_after_hand_back(task.attempt_count)
    task.last_error = reason
    clear_lease(task)
    clear_claim(task)
