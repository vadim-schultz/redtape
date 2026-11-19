"""SQL clauses and statements that decide which discovery tasks are leasable or expired."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ColumnElement, Update, func, or_, select, update

from app.models.discovery import DiscoveryFailureClass, DiscoveryTask, DiscoveryTaskStatus


def delayed(now: datetime) -> tuple[ColumnElement[bool], ...]:
    """Return the predicates for a pending task held back until after ``now``."""
    return (DiscoveryTask.status == DiscoveryTaskStatus.PENDING, DiscoveryTask.not_before > now)


def claimable(now: datetime) -> tuple[ColumnElement[bool], ...]:
    """Return the predicates that make a task leasable at ``now``: pending and past its ``not_before``."""
    return (
        DiscoveryTask.status == DiscoveryTaskStatus.PENDING,
        or_(DiscoveryTask.not_before.is_(None), DiscoveryTask.not_before <= now),
    )


def expired_lease(now: datetime) -> tuple[ColumnElement[bool], ...]:
    """Return the predicates that mark a claimed task whose lease ended before ``now``."""
    return (
        DiscoveryTask.status == DiscoveryTaskStatus.CLAIMED,
        DiscoveryTask.lease_expires_at.is_not(None),
        DiscoveryTask.lease_expires_at < now,
    )


def fail_exhausted_stmt(now: datetime, max_attempts: int) -> Update:
    """Fail every expired lease whose task has used all its attempts, recording why."""
    message = func.concat("lease expired after ", DiscoveryTask.attempt_count, " attempts")
    return (
        update(DiscoveryTask)
        .where(*expired_lease(now), DiscoveryTask.attempt_count >= max_attempts)
        .values(status=DiscoveryTaskStatus.FAILED, last_error=message, lease_expires_at=None)
    )


def repend_expired_stmt(now: datetime) -> Update:
    """Return expired leases to pending and clear their claim so another worker can take them."""
    return (
        update(DiscoveryTask)
        .where(*expired_lease(now))
        .values(
            status=DiscoveryTaskStatus.PENDING,
            claimed_by_api_key_id=None,
            claimed_at=None,
            lease_expires_at=None,
        )
    )


def requeue_transient_stmt(cutoff: datetime, limit: int) -> Update:
    """Return up to ``limit`` failed transient tasks last failed before ``cutoff`` to pending, with a fresh attempt count.

    Only the transient class is selected; a permanent, login-wall, robots, not-found or unclassified failure is left alone.
    """
    due = (
        select(DiscoveryTask.id)
        .where(
            DiscoveryTask.status == DiscoveryTaskStatus.FAILED,
            DiscoveryTask.failure_class == DiscoveryFailureClass.TRANSIENT,
            DiscoveryTask.updated_at <= cutoff,
        )
        .order_by(DiscoveryTask.updated_at.asc(), DiscoveryTask.id.asc())
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    return (
        update(DiscoveryTask)
        .where(DiscoveryTask.id.in_(due))
        .values(status=DiscoveryTaskStatus.PENDING, attempt_count=0, not_before=None, failure_class=None)
        .returning(DiscoveryTask.id)
    )
