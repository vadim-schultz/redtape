"""Failed discovery tasks: the failure class is persisted, and only transient failures return after the cooldown."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.features.discovery.repository import DiscoveryRepository, TaskTarget
from app.features.discovery.task_queue import TaskQueue
from app.models.api_key import ApiKey
from app.models.discovery import CatalogueService, DiscoveryTask, DiscoveryTaskKind, DiscoveryTaskStatus
from sqlalchemy.orm import Session

from test_discovery_admin_api import _catalogue

NOW = datetime(2026, 11, 19, 12, 0, tzinfo=UTC)
FETCH = (DiscoveryTaskKind.FETCH_URL,)


def _row(session: Session, task_id: uuid.UUID) -> DiscoveryTask:
    row = session.get(DiscoveryTask, task_id)
    assert row is not None
    return row


def _key(session: Session) -> ApiKey:
    key = ApiKey(name="requeue", key_hash=uuid.uuid4().hex * 2, key_prefix=uuid.uuid4().hex[:8])
    session.add(key)
    session.flush()
    return key


def _failed(
    session: Session,
    catalogue: CatalogueService,
    *,
    failure_class: str | None,
    age: timedelta,
    attempts: int = 3,
) -> DiscoveryTask:
    """Return a failed fetch task whose last failure is ``age`` old, with ``failure_class`` recorded."""
    target = TaskTarget(
        catalogue_service_id=catalogue.id,
        kind=DiscoveryTaskKind.FETCH_URL,
        target_url=f"https://example.gov/{uuid.uuid4().hex}",
    )
    task = DiscoveryRepository(session).insert_task(target)
    task.status = DiscoveryTaskStatus.FAILED
    task.failure_class = failure_class
    task.attempt_count = attempts
    task.last_error = "http 503"
    task.updated_at = NOW - age
    session.flush()
    return task


def _requeue(session: Session, *, limit: int = 50) -> int:
    return TaskQueue(DiscoveryRepository(session)).requeue_transient(limit=limit, now=NOW)


def _claimed_fetch(session: Session, catalogue: CatalogueService) -> DiscoveryTask:
    """Enqueue one fetch task for ``catalogue`` and claim it to a fresh key."""
    queue = TaskQueue(DiscoveryRepository(session))
    task = queue.enqueue(
        TaskTarget(
            catalogue_service_id=catalogue.id,
            kind=DiscoveryTaskKind.FETCH_URL,
            target_url=f"https://example.gov/{uuid.uuid4().hex}",
        )
    ).task
    queue.claim_pending(api_key=_key(session), limit=1, now=NOW, kinds=FETCH)
    return task


def test_a_permanent_failure_and_a_login_wall_are_never_requeued(db_session: Session) -> None:
    """discovery requeue · negative: permanent, login_wall, robots, not_found and unrecorded failures stay failed."""
    catalogue = _catalogue(db_session)
    kept = [
        _failed(db_session, catalogue, failure_class=failure_class, age=timedelta(hours=30))
        for failure_class in ("permanent", "login_wall", "robots", "not_found", None)
    ]
    transient = _failed(db_session, catalogue, failure_class="transient", age=timedelta(hours=30))

    requeued = _requeue(db_session)

    assert requeued == 1
    assert {_row(db_session, task.id).status for task in kept} == {DiscoveryTaskStatus.FAILED}
    assert _row(db_session, transient.id).status is DiscoveryTaskStatus.PENDING


def test_a_transient_failure_is_requeued_only_after_the_cooldown(db_session: Session) -> None:
    """discovery requeue · happy: a transient failure 25 h old returns; one 2 h old waits."""
    catalogue = _catalogue(db_session)
    due = _failed(db_session, catalogue, failure_class="transient", age=timedelta(hours=25))
    early = _failed(db_session, catalogue, failure_class="transient", age=timedelta(hours=2))

    requeued = _requeue(db_session)

    assert requeued == 1
    assert _row(db_session, due.id).status is DiscoveryTaskStatus.PENDING
    assert _row(db_session, early.id).status is DiscoveryTaskStatus.FAILED


def test_a_requeued_task_starts_with_a_fresh_attempt_count(db_session: Session) -> None:
    """discovery requeue · happy: attempt_count is 0 and the last error stays for the operator."""
    catalogue = _catalogue(db_session)
    task = _failed(db_session, catalogue, failure_class="transient", age=timedelta(hours=25), attempts=3)

    _requeue(db_session)

    refreshed = _row(db_session, task.id)
    assert refreshed.attempt_count == 0
    assert refreshed.status is DiscoveryTaskStatus.PENDING
    assert refreshed.last_error == "http 503"


def test_a_failure_class_is_stored_with_the_failure(db_session: Session) -> None:
    """discovery fail · happy: the class the worker sends is persisted on the task."""
    catalogue = _catalogue(db_session)
    task = _claimed_fetch(db_session, catalogue)

    TaskQueue(DiscoveryRepository(db_session)).fail(
        task.id, "robots.txt disallows", retryable=False, now=NOW, failure_class="robots"
    )

    assert _row(db_session, task.id).failure_class == "robots"


def test_a_failure_without_a_class_stores_none_and_is_never_requeued(db_session: Session) -> None:
    """discovery fail · negative: a worker that sends no class leaves the row unclassified, so it is not requeued."""
    catalogue = _catalogue(db_session)
    task = _claimed_fetch(db_session, catalogue)
    TaskQueue(DiscoveryRepository(db_session)).fail(task.id, "http 503", retryable=False, now=NOW)
    _row(db_session, task.id).updated_at = NOW - timedelta(hours=30)
    db_session.flush()

    assert _row(db_session, task.id).failure_class is None
    assert _requeue(db_session) == 0
