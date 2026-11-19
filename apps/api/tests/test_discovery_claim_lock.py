"""Discovery claims lock the task rows they lease: two claimers on their own connections never share a task."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.db import engine as db_engine
from app.features.discovery.repository import DiscoveryRepository, TaskTarget
from app.features.discovery.task_queue import TaskQueue
from app.models.api_key import ApiKey
from app.models.discovery import CatalogueService, DiscoveryTask, DiscoveryTaskKind
from app.models.jurisdiction import Jurisdiction
from sqlalchemy import delete, text
from sqlalchemy.orm import Session

from test_discovery_admin_api import _catalogue

FETCH = (DiscoveryTaskKind.FETCH_URL,)


@dataclass
class CommittedTasks:
    """The rows committed for one test; deleted again on exit."""

    catalogue_id: uuid.UUID
    jurisdiction_id: uuid.UUID
    key_ids: list[uuid.UUID] = field(default_factory=list)


@contextmanager
def _committed_tasks(count: int) -> Iterator[CommittedTasks]:
    """Commit one catalogue service with ``count`` pending fetch tasks and two API keys; delete them on exit."""
    with Session(bind=db_engine, expire_on_commit=False) as session:
        catalogue = _catalogue(session, external_id=f"lock-{uuid.uuid4().hex[:8]}")
        for index in range(count):
            DiscoveryRepository(session).insert_task(
                TaskTarget(
                    catalogue_service_id=catalogue.id,
                    kind=DiscoveryTaskKind.FETCH_URL,
                    target_url=f"https://example.gov/lock/{index}",
                )
            )
        keys = [
            ApiKey(name=f"lock-{n}", key_hash=uuid.uuid4().hex * 2, key_prefix=uuid.uuid4().hex[:8]) for n in (1, 2)
        ]
        session.add_all(keys)
        session.flush()
        world = CommittedTasks(catalogue.id, catalogue.jurisdiction_id, [key.id for key in keys])
        session.commit()
        try:
            yield world
        finally:
            _forget(session, world)


def _forget(session: Session, world: CommittedTasks) -> None:
    """Delete the committed catalogue (its tasks cascade), jurisdiction and keys."""
    session.execute(delete(CatalogueService).where(CatalogueService.id == world.catalogue_id))
    session.execute(delete(Jurisdiction).where(Jurisdiction.id == world.jurisdiction_id))
    session.execute(delete(ApiKey).where(ApiKey.id.in_(world.key_ids)))
    session.commit()


def test_two_claimers_never_receive_the_same_task(db_session: Session) -> None:
    """discovery claim · both claims run in open transactions on their own connections; the union has no duplicates."""
    with _committed_tasks(6) as world:
        with Session(bind=db_engine) as first, Session(bind=db_engine) as second:
            second.execute(text("SET LOCAL lock_timeout = '3s'"))
            from_a = _claim(first, world.key_ids[0], limit=3)
            from_b = _claim(second, world.key_ids[1], limit=3)
            ids_a, ids_b = {task.id for task in from_a}, {task.id for task in from_b}
            first.commit()
            second.commit()

        assert len(ids_a) == len(ids_b) == 3
        assert ids_a.isdisjoint(ids_b)


def test_a_claimer_does_not_wait_for_rows_another_claim_holds(db_session: Session) -> None:
    """discovery claim · while one claim holds every row, a second claim returns at once with nothing (SKIP LOCKED)."""
    with _committed_tasks(3) as world:
        with Session(bind=db_engine) as first, Session(bind=db_engine) as second:
            second.execute(text("SET LOCAL lock_timeout = '3s'"))
            held = _claim(first, world.key_ids[0], limit=3)
            waiting = _claim(second, world.key_ids[1], limit=3)
            first.commit()
            second.commit()

        assert len(held) == 3
        assert waiting == []


def _claim(session: Session, key_id: uuid.UUID, *, limit: int) -> list[DiscoveryTask]:
    """Claim up to ``limit`` fetch tasks for the key on ``session``; the claimed rows stay locked until commit."""
    key = session.get(ApiKey, key_id)
    assert key is not None
    queue = TaskQueue(DiscoveryRepository(session))
    return queue.claim_pending(api_key=key, limit=limit, now=datetime.now(UTC), kinds=FETCH)
