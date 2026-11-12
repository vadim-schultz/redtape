"""Upsert of the snapshot task (chapter 07): a pending row takes the new priority; a claimed row is left alone."""

from __future__ import annotations

import uuid

from app.features.translation.task_repository import TaskRepository
from app.models.search import WorkTaskStatus
from app.models.snapshot_translation import SnapshotTranslationTask
from sqlalchemy import select
from sqlalchemy.orm import Session

from embedding_support import make_key
from test_snapshot_models import catalogue_row

OLD, NEW = "a" * 64, "b" * 64


def _rows(session: Session, catalogue_id: uuid.UUID) -> list[SnapshotTranslationTask]:
    stmt = (
        select(SnapshotTranslationTask)
        .where(SnapshotTranslationTask.catalogue_service_id == catalogue_id)
        .order_by(SnapshotTranslationTask.created_at, SnapshotTranslationTask.id)
        .execution_options(populate_existing=True)
    )
    return list(session.scalars(stmt))


def test_a_pending_row_takes_the_new_priority_and_an_unchanged_repeat_writes_nothing(db_session: Session) -> None:
    """upsert · a pending row's priority is updated; a repeat with the same values changes nothing."""
    catalogue = catalogue_row(db_session)
    repo = TaskRepository(db_session)
    key = (catalogue.id, "en")

    queued = repo.upsert_snapshot_pending(key, OLD, 500)
    reprioritised = repo.upsert_snapshot_pending(key, OLD, 300)
    repeated = repo.upsert_snapshot_pending(key, OLD, 300)

    (task,) = _rows(db_session, catalogue.id)
    assert (queued, reprioritised, repeated) == (True, True, False)
    assert (task.status, task.priority, task.source_hash) == (WorkTaskStatus.PENDING, 300, OLD)


def test_a_claimed_row_is_left_unchanged_and_no_second_row_is_added(db_session: Session) -> None:
    """upsert · a claimed row keeps its priority and hash, and no second open row is added beside it."""
    catalogue = catalogue_row(db_session)
    repo = TaskRepository(db_session)
    key = (catalogue.id, "en")
    repo.upsert_snapshot_pending(key, OLD, 500)
    (task,) = _rows(db_session, catalogue.id)
    task.status = WorkTaskStatus.CLAIMED
    task.claimed_by_api_key_id = make_key(db_session).id
    db_session.flush()

    changed = repo.upsert_snapshot_pending(key, NEW, 5)

    (after,) = _rows(db_session, catalogue.id)
    assert changed is False
    assert (after.status, after.priority, after.source_hash) == (WorkTaskStatus.CLAIMED, 500, OLD)


def test_a_completed_row_is_not_reopened_and_the_new_work_is_a_separate_pending_row(db_session: Session) -> None:
    """upsert · a completed row is never changed by the upsert; new work is queued as its own pending row."""
    catalogue = catalogue_row(db_session)
    db_session.add(
        SnapshotTranslationTask(
            catalogue_service_id=catalogue.id,
            locale="en",
            source_hash=OLD,
            priority=500,
            status=WorkTaskStatus.COMPLETED,
        )
    )
    db_session.flush()

    queued = TaskRepository(db_session).upsert_snapshot_pending((catalogue.id, "en"), NEW, 300)

    completed, pending = sorted(
        _rows(db_session, catalogue.id), key=lambda task: task.status != WorkTaskStatus.COMPLETED
    )
    assert queued is True
    assert (completed.status, completed.priority, completed.source_hash) == (WorkTaskStatus.COMPLETED, 500, OLD)
    assert (pending.status, pending.priority, pending.source_hash) == (WorkTaskStatus.PENDING, 300, NEW)
