"""Retention: fetch logs and events past the window are pruned in batches, and the latest fetch of every target survives."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.features.discovery.repository import DiscoveryRepository, FetchLogEntry, NewEvent, TaskTarget
from app.features.discovery.retention import DiscoveryRetentionService
from app.models.discovery import (
    CatalogueService,
    DiscoveryEvent,
    DiscoveryEventType,
    DiscoveryFetchLog,
    DiscoveryTask,
    DiscoveryTaskKind,
)
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from test_discovery_admin_api import _catalogue
from test_discovery_machine_api import _issue_key
from test_discovery_machine_api import client as machine_client  # noqa: F401

NOW = datetime(2026, 11, 19, 12, tzinfo=UTC)
WINDOW = timedelta(days=180)
PAGE = "https://portal.example/service/1"
OTHER_PAGE = "https://portal.example/service/2"
PRUNE_URL = "/api/v1/discovery/machine/retention/prune"


def _task(session: Session, catalogue: CatalogueService, url: str, kind: DiscoveryTaskKind) -> DiscoveryTask:
    """Insert a task of ``kind`` for ``url`` on the catalogue row."""
    target = TaskTarget(catalogue_service_id=catalogue.id, kind=kind, target_url=url)
    return DiscoveryRepository(session).insert_task(target)


def _fetch(session: Session, task: DiscoveryTask, *, days_ago: int) -> uuid.UUID:
    """Insert a fetch log for ``task`` fetched ``days_ago`` days before ``NOW``; return its id."""
    entry = FetchLogEntry(
        discovery_task_id=task.id,
        http_status=200,
        content_type="text/html",
        byte_length=10,
        error_message=None,
        fetched_at=NOW - timedelta(days=days_ago),
    )
    row = DiscoveryRepository(session).append_fetch_log(entry)
    session.flush()
    return row.id


def _event(session: Session, catalogue: CatalogueService, *, days_ago: int) -> uuid.UUID:
    """Insert a fetch-logged event created ``days_ago`` days before ``NOW``; return its id."""
    row = DiscoveryRepository(session).record_event(
        NewEvent(event_type=DiscoveryEventType.FETCH_LOGGED, catalogue_service_id=catalogue.id, payload={})
    )
    row.created_at = NOW - timedelta(days=days_ago)
    session.flush()
    return row.id


def _service(session: Session, *, batch_size: int = 1000) -> DiscoveryRetentionService:
    """Return the retention service over the session with the 180-day window."""
    return DiscoveryRetentionService(DiscoveryRepository(session), retention=WINDOW, batch_size=batch_size)


def _surviving_fetch_ids(session: Session) -> set[uuid.UUID]:
    """Return the ids of every fetch log still in the table."""
    return set(session.scalars(select(DiscoveryFetchLog.id)).all())


def test_the_retention_job_keeps_the_latest_fetch_of_every_target(db_session: Session) -> None:
    """retention · negative: past the window, only the newest fetch of each target survives; older ones are pruned."""
    catalogue = _catalogue(db_session)
    page = _task(db_session, catalogue, PAGE, DiscoveryTaskKind.FETCH_URL)
    other = _task(db_session, catalogue, OTHER_PAGE, DiscoveryTaskKind.FETCH_URL)
    old_page_first = _fetch(db_session, page, days_ago=400)
    old_page_latest = _fetch(db_session, page, days_ago=300)
    only_other = _fetch(db_session, other, days_ago=500)

    totals = _service(db_session).prune(now=NOW)

    assert _surviving_fetch_ids(db_session) == {old_page_latest, only_other}
    assert old_page_first not in _surviving_fetch_ids(db_session)
    assert totals.fetch_logs == 1


def test_a_fetch_inside_the_window_is_never_pruned(db_session: Session) -> None:
    """retention · negative: a fetch younger than the window stays, even when a newer fetch of the same target exists."""
    catalogue = _catalogue(db_session)
    page = _task(db_session, catalogue, PAGE, DiscoveryTaskKind.FETCH_URL)
    inside = _fetch(db_session, page, days_ago=30)
    newest = _fetch(db_session, page, days_ago=10)

    _service(db_session).prune(now=NOW)

    assert _surviving_fetch_ids(db_session) == {inside, newest}


def test_events_past_the_window_are_pruned_and_newer_ones_kept(db_session: Session) -> None:
    """retention · happy: an event created before the window is deleted; one created inside it is kept."""
    catalogue = _catalogue(db_session)
    expired = _event(db_session, catalogue, days_ago=200)
    recent = _event(db_session, catalogue, days_ago=20)

    totals = _service(db_session).prune(now=NOW)

    remaining = set(db_session.scalars(select(DiscoveryEvent.id)).all())
    assert expired not in remaining and recent in remaining
    assert totals.events == 1


def test_the_prune_works_in_batches_and_reports_every_row_it_deleted(db_session: Session) -> None:
    """retention · happy: five expired events and a batch size of two take three batches and delete all five."""
    catalogue = _catalogue(db_session)
    for days_ago in (200, 201, 202, 203, 204):
        _event(db_session, catalogue, days_ago=days_ago)

    totals = _service(db_session, batch_size=2).prune(now=NOW)

    remaining = db_session.scalars(select(DiscoveryEvent.id).where(DiscoveryEvent.created_at < NOW - WINDOW)).all()
    assert remaining == []
    assert totals.events == 5


def test_the_prune_route_answers_with_the_rows_it_deleted(
    machine_client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
) -> None:
    """retention · happy: the machine route prunes past the window and answers with both counts."""
    catalogue = _catalogue(db_session)
    _event(db_session, catalogue, days_ago=900)
    key = _issue_key(db_session)

    response = machine_client.post(PRUNE_URL, headers={"X-API-Key": key})

    assert response.status_code == 200
    assert response.json()["events_deleted"] >= 1
    assert set(response.json()) == {"fetch_logs_deleted", "events_deleted"}


def test_the_prune_route_refuses_a_caller_without_a_machine_key(
    machine_client: TestClient[Litestar],  # noqa: F811
) -> None:
    """retention · negative: without a machine key the prune is refused and nothing is deleted."""
    response = machine_client.post(PRUNE_URL)

    assert response.status_code == 401
