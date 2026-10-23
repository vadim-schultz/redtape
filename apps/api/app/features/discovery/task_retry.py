"""Retry policy for failed discovery tasks: attempt cap and backoff."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.models.discovery import DiscoveryTask, DiscoveryTaskStatus

MAX_ATTEMPTS = 3
BACKOFF: tuple[timedelta, ...] = (timedelta(minutes=5), timedelta(minutes=30), timedelta(hours=3))


def settle_failure(task: DiscoveryTask, error: str, *, retryable: bool, now: datetime) -> None:
    """Record ``error``; re-pend ``task`` with backoff if retryable and under the cap, else fail it."""
    task.last_error = error
    task.lease_expires_at = None
    if retryable and task.attempt_count < MAX_ATTEMPTS:
        _repend(task, now)
    else:
        task.status = DiscoveryTaskStatus.FAILED


def _repend(task: DiscoveryTask, now: datetime) -> None:
    attempt = min(max(task.attempt_count, 1), len(BACKOFF))
    task.status = DiscoveryTaskStatus.PENDING
    task.not_before = now + BACKOFF[attempt - 1]
    task.claimed_at = None
    task.claimed_by_api_key_id = None
