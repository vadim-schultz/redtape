"""SQL clauses and statements that decide which discovery tasks are leasable or expired."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import ColumnElement, Select, Update, exists, func, or_, select, update
from sqlalchemy.orm import aliased

from app.models.discovery import DiscoveryFailureClass, DiscoveryTask, DiscoveryTaskKind, DiscoveryTaskStatus


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


def _superseded(kind: DiscoveryTaskKind, input_key: str) -> tuple[ColumnElement[bool], ...]:
    """Return the predicates of a completed ``kind`` task under another key, whose page has no task under ``input_key``."""
    current = aliased(DiscoveryTask)
    page_has_current_key = exists().where(
        current.catalogue_service_id == DiscoveryTask.catalogue_service_id,
        current.kind == DiscoveryTask.kind,
        current.target_url == DiscoveryTask.target_url,
        current.input_key == input_key,
    )
    return (
        DiscoveryTask.kind == kind,
        DiscoveryTask.status == DiscoveryTaskStatus.COMPLETED,
        DiscoveryTask.input_key.is_not(None),
        DiscoveryTask.input_key != input_key,
        DiscoveryTask.artifact_id.is_not(None),
        ~page_has_current_key,
    )


def superseded_ids_stmt(kind: DiscoveryTaskKind, input_key: str, limit: int) -> Select[tuple[UUID]]:
    """Return up to ``limit`` ids of superseded tasks, one per page, the newest completion of each page first."""
    newest_per_page = (
        select(DiscoveryTask.id)
        .distinct(DiscoveryTask.catalogue_service_id, DiscoveryTask.target_url)
        .where(*_superseded(kind, input_key))
        .order_by(
            DiscoveryTask.catalogue_service_id,
            DiscoveryTask.target_url,
            DiscoveryTask.updated_at.desc(),
            DiscoveryTask.id,
        )
    )
    return select(DiscoveryTask.id).where(DiscoveryTask.id.in_(newest_per_page)).limit(limit)


def requeue_superseded_stmt(ids: Select[tuple[UUID]], input_key: str) -> Update:
    """Re-pend the selected superseded tasks under ``input_key``, with a fresh attempt count and their old result cleared."""
    return (
        update(DiscoveryTask)
        .where(DiscoveryTask.id.in_(ids))
        .values(
            status=DiscoveryTaskStatus.PENDING,
            input_key=input_key,
            attempt_count=0,
            not_before=None,
            last_error=None,
            result_note=None,
            text_hash=None,
            failure_class=None,
        )
        .returning(DiscoveryTask.id)
    )
