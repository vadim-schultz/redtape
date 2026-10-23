"""Unit tests for the discovery task queue collaborator."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.features.discovery.errors import DiscoveryTaskNotFoundError
from app.features.discovery.repository import DiscoveryRepository, TaskTarget
from app.features.discovery.task_queue import TaskQueue
from app.models.api_key import ApiKey
from app.models.discovery import CatalogueService, DiscoveryTask, DiscoveryTaskKind, DiscoveryTaskStatus
from sqlalchemy.orm import Session

from test_discovery_admin_api import _catalogue


@pytest.fixture
def queue(db_session: Session) -> TaskQueue:
    return TaskQueue(DiscoveryRepository(db_session))


def test_enqueue_for_service_creates_a_pending_task_for_a_portal_url(queue: TaskQueue, db_session: Session) -> None:
    catalogue = _catalogue(db_session)
    catalogue.portal_url = "https://example.gov/portal"

    task = queue.enqueue_for_service(catalogue)

    assert task is not None
    assert task.status == DiscoveryTaskStatus.PENDING
    assert task.target_url == "https://example.gov/portal"


def test_enqueue_for_service_without_portal_url_creates_nothing(queue: TaskQueue, db_session: Session) -> None:
    catalogue = _catalogue(db_session)
    catalogue.portal_url = None

    assert queue.enqueue_for_service(catalogue) is None


def test_claim_pending_leases_enqueued_tasks_to_the_key(queue: TaskQueue, db_session: Session) -> None:
    catalogue = _catalogue(db_session)
    catalogue.portal_url = "https://example.gov/portal"
    queue.enqueue_for_service(catalogue)
    key = ApiKey(name="k", key_hash="h" * 64, key_prefix="p" * 8)
    db_session.add(key)
    db_session.flush()

    claimed = queue.claim_pending(api_key=key, limit=5, now=datetime.now(UTC))

    assert [t.status for t in claimed] == [DiscoveryTaskStatus.CLAIMED]
    assert claimed[0].claimed_by_api_key_id == key.id
    assert claimed[0].lease_expires_at is not None


def test_complete_and_fail_reject_unknown_task_ids(queue: TaskQueue) -> None:
    with pytest.raises(DiscoveryTaskNotFoundError):
        queue.complete(uuid.uuid4())
    with pytest.raises(DiscoveryTaskNotFoundError):
        queue.fail(uuid.uuid4(), "boom")


def _key(db_session: Session) -> ApiKey:
    key = ApiKey(name="k", key_hash="h" * 64, key_prefix="p" * 8)
    db_session.add(key)
    db_session.flush()
    return key


def _seed_task(
    db_session: Session,
    catalogue: CatalogueService,
    kind: DiscoveryTaskKind,
    *,
    path: str,
    priority: int = 100,
    age_minutes: int = 0,
) -> DiscoveryTask:
    target = TaskTarget(catalogue_service_id=catalogue.id, kind=kind, target_url=f"https://example.gov/{path}")
    task = DiscoveryRepository(db_session).insert_task(target, priority=priority)
    task.created_at = datetime.now(UTC) - timedelta(minutes=age_minutes)
    db_session.flush()
    return task


def test_claim_pending_without_kinds_ignores_new_task_kinds(queue: TaskQueue, db_session: Session) -> None:
    catalogue = _catalogue(db_session)
    legacy = _seed_task(db_session, catalogue, DiscoveryTaskKind.FETCH_URL, path="fetch")
    new = _seed_task(db_session, catalogue, DiscoveryTaskKind.EXTRACT_PAGE, path="extract")

    claimed = queue.claim_pending(api_key=_key(db_session), limit=10, now=datetime.now(UTC))

    assert [t.id for t in claimed] == [legacy.id]
    assert new.status == DiscoveryTaskStatus.PENDING


def test_claim_pending_with_kinds_returns_only_those_kinds_in_queue_order(
    queue: TaskQueue, db_session: Session
) -> None:
    catalogue = _catalogue(db_session)
    late = _seed_task(db_session, catalogue, DiscoveryTaskKind.EXTRACT_PAGE, path="late", age_minutes=1)
    early = _seed_task(db_session, catalogue, DiscoveryTaskKind.EXTRACT_PAGE, path="early", age_minutes=9)
    urgent = _seed_task(db_session, catalogue, DiscoveryTaskKind.CAPTURE_SCREENSHOT, path="urgent", priority=10)
    _seed_task(db_session, catalogue, DiscoveryTaskKind.FETCH_URL, path="legacy", priority=1)

    kinds = (DiscoveryTaskKind.EXTRACT_PAGE, DiscoveryTaskKind.CAPTURE_SCREENSHOT)
    claimed = queue.claim_pending(api_key=_key(db_session), limit=10, now=datetime.now(UTC), kinds=kinds)

    assert [t.id for t in claimed] == [urgent.id, early.id, late.id]
