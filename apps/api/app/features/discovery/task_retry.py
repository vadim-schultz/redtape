"""Retry policy for failed leased tasks: attempt cap and backoff."""

from __future__ import annotations

import enum
from datetime import datetime, timedelta
from typing import Final, Protocol

from app.features.discovery.task_lease import LeaseFields, clear_claim, clear_lease
from app.models.discovery import DiscoveryTask, DiscoveryTaskStatus

MAX_ATTEMPTS: Final = 3
BACKOFF: Final[tuple[timedelta, ...]] = (timedelta(minutes=5), timedelta(minutes=30), timedelta(hours=3))


class FailureKind(enum.StrEnum):
    """Whether a failure may be tried again after a backoff."""

    RETRYABLE = "retryable"
    PERMANENT = "permanent"


class RetryFields(LeaseFields, Protocol):
    """The columns the retry policy reads and writes on any leased task row."""

    attempt_count: int
    last_error: str | None
    not_before: datetime | None


def apply_retry_policy(task: RetryFields, error: str, kind: FailureKind, now: datetime) -> bool:
    """Record ``error`` on ``task``; return ``True`` when it goes back to the queue after a backoff, ``False`` to fail it.

    The caller sets the status, because each table has its own status enum.
    """
    task.last_error = error
    clear_lease(task)
    if kind is FailureKind.PERMANENT or task.attempt_count >= MAX_ATTEMPTS:
        return False
    attempt = min(max(task.attempt_count, 1), len(BACKOFF))
    task.not_before = now + BACKOFF[attempt - 1]
    clear_claim(task)
    return True


def settle_failure(task: DiscoveryTask, error: str, *, retryable: bool, now: datetime) -> None:
    """Record ``error``; re-pend ``task`` with backoff if retryable and under the cap, else fail it."""
    kind = FailureKind.RETRYABLE if retryable else FailureKind.PERMANENT
    repended = apply_retry_policy(task, error, kind, now)
    task.status = DiscoveryTaskStatus.PENDING if repended else DiscoveryTaskStatus.FAILED
