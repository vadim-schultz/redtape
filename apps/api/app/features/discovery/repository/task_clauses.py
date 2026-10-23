"""SQL clauses and statements that decide which discovery tasks are leasable or expired."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ColumnElement, Update, func, or_, update

from app.models.discovery import DiscoveryTask, DiscoveryTaskStatus


def claimable(now: datetime) -> tuple[ColumnElement[bool], ...]:
    """Return the predicates that make a task leasable at ``now``: pending and past its ``not_before``."""
    return (
        DiscoveryTask.status == DiscoveryTaskStatus.PENDING,
        or_(DiscoveryTask.not_before.is_(None), DiscoveryTask.not_before <= now),
    )


def _expired_lease(now: datetime) -> tuple[ColumnElement[bool], ...]:
    return (
        DiscoveryTask.status == DiscoveryTaskStatus.CLAIMED,
        DiscoveryTask.lease_expires_at.is_not(None),
        DiscoveryTask.lease_expires_at < now,
    )


def fail_exhausted_stmt(now: datetime, max_attempts: int) -> Update:
    message = func.concat("lease expired after ", DiscoveryTask.attempt_count, " attempts")
    return (
        update(DiscoveryTask)
        .where(*_expired_lease(now), DiscoveryTask.attempt_count >= max_attempts)
        .values(status=DiscoveryTaskStatus.FAILED, last_error=message, lease_expires_at=None)
    )


def repend_expired_stmt(now: datetime) -> Update:
    return (
        update(DiscoveryTask)
        .where(*_expired_lease(now))
        .values(
            status=DiscoveryTaskStatus.PENDING,
            claimed_by_api_key_id=None,
            claimed_at=None,
            lease_expires_at=None,
        )
    )
