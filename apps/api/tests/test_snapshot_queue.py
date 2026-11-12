"""Claim and reclaim of the snapshot task queue on the shared leased queue (chapter 07)."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.features.discovery.task_retry import MAX_ATTEMPTS
from app.features.search.leased_queue import LeasedQueue
from app.models.api_key import ApiKey
from app.models.search import WorkTaskStatus
from app.models.snapshot_translation import SnapshotTranslationTask
from sqlalchemy.orm import Session

from embedding_support import NOW, make_key
from test_snapshot_models import catalogue_row

HASH = "a" * 64
LEASE = timedelta(minutes=15)
LATER = NOW + timedelta(minutes=16)


def _queue(session: Session) -> LeasedQueue[SnapshotTranslationTask]:
    return LeasedQueue(session, SnapshotTranslationTask)


def _queued(session: Session, priority: int, created_at: datetime) -> SnapshotTranslationTask:
    task = SnapshotTranslationTask(
        catalogue_service_id=catalogue_row(session).id,
        locale="en",
        source_hash=HASH,
        priority=priority,
        created_at=created_at,
    )
    session.add(task)
    session.flush()
    return task


def _claimed(session: Session, task: SnapshotTranslationTask, key: ApiKey) -> None:
    """Put ``task`` in the state a claim by ``key`` leaves it in, with that claim counted as one more attempt."""
    task.status = WorkTaskStatus.CLAIMED
    task.claimed_by_api_key_id = key.id
    task.claimed_at = NOW
    task.lease_expires_at = NOW + LEASE
    task.attempt_count += 1
    session.flush()


def test_claim_orders_by_priority_then_age_for_the_snapshot_model(db_session: Session) -> None:
    """queue · claim orders by priority, then age, for the snapshot model, and honours the limit."""
    old = _queued(db_session, 100, NOW - timedelta(hours=2))
    new = _queued(db_session, 100, NOW - timedelta(hours=1))
    urgent = _queued(db_session, 10, NOW)

    claimed = _queue(db_session).claim(make_key(db_session).id, NOW, 2, ())

    assert [task.id for task in claimed] == [urgent.id, old.id]
    assert new.status is WorkTaskStatus.PENDING


def test_an_expired_lease_is_reclaimed_by_another_key(db_session: Session) -> None:
    """queue · an expired lease is reclaimed by another key, and the attempt is counted again."""
    task = _queued(db_session, 100, NOW)
    first, second = make_key(db_session, "first"), make_key(db_session, "second")
    _claimed(db_session, task, first)

    reclaimed = _queue(db_session).claim(second.id, LATER, 5, ())

    assert [item.id for item in reclaimed] == [task.id]
    assert (task.claimed_by_api_key_id, task.attempt_count) == (second.id, 2)


def test_an_expired_lease_at_the_attempt_cap_is_failed_and_not_leased_again(db_session: Session) -> None:
    """queue · a task whose expired lease used every attempt is failed, not handed out again."""
    task = _queued(db_session, 100, NOW)
    task.attempt_count = MAX_ATTEMPTS - 1
    _claimed(db_session, task, make_key(db_session, "holder"))

    claimed = _queue(db_session).claim(make_key(db_session, "other").id, LATER, 5, ())

    assert claimed == []
    assert (task.status, task.last_error) == (WorkTaskStatus.FAILED, f"lease expired after {MAX_ATTEMPTS} attempts")
