"""Catalogue refresh: a bounded weekly re-fetch of stale pages through the existing enqueue, and a change gate that compares with the page's last body."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.features.discovery.render_gate import refresh_key
from app.features.discovery.repository import DiscoveryRepository, TaskTarget
from app.models.discovery import DiscoveryFetchLog, DiscoveryTask, DiscoveryTaskKind, DiscoveryTaskStatus
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from test_discovery_admin_api import _catalogue
from test_discovery_machine_api import _issue_key
from test_discovery_machine_api import client as machine_client  # noqa: F401
from test_discovery_render_gate import HASH_A, HASH_B, PAGE_URL, _completed_render, _fetch

STALE_URL = "/api/v1/discovery/machine/catalogue/stale-fetches"
ENQUEUE_URL = "/api/v1/discovery/machine/tasks"


def _page_target(catalogue_id: uuid.UUID, *, input_key: str | None = None) -> TaskTarget:
    """Return the identity of a fetch_url task for the portal page, under ``input_key`` when one is given."""
    return TaskTarget(
        catalogue_service_id=catalogue_id,
        kind=DiscoveryTaskKind.FETCH_URL,
        target_url=PAGE_URL,
        input_key=input_key,
    )


def _page(session: Session, external_id: str, *, fetched_days_ago: float | None) -> tuple[uuid.UUID, uuid.UUID]:
    """Insert a catalogue row whose portal is the page, with its base fetch_url task and, when given, one fetch logged that many days ago.

    Return the catalogue row id and the base task id.
    """
    catalogue = _catalogue(session, external_id=external_id)
    catalogue.portal_url = PAGE_URL
    session.flush()
    task = DiscoveryRepository(session).insert_task(_page_target(catalogue.id))
    task.status = DiscoveryTaskStatus.COMPLETED
    if fetched_days_ago is not None:
        _log_fetch(session, task.id, datetime.now(UTC) - timedelta(days=fetched_days_ago))
    session.flush()
    return catalogue.id, task.id


def _log_fetch(session: Session, task_id: uuid.UUID, fetched_at: datetime) -> None:
    """Record one successful fetch of a task at ``fetched_at``."""
    session.add(
        DiscoveryFetchLog(
            discovery_task_id=task_id,
            http_status=200,
            content_type="text/html",
            byte_length=10,
            fetched_at=fetched_at,
            body_sha256=HASH_A,
        )
    )


def _stale(client: TestClient[Litestar], key: str, *, limit: int = 10) -> dict[str, object]:
    """Read the stale-fetch listing with ``limit``; return the JSON answer."""
    response = client.get(STALE_URL, params={"limit": limit}, headers={"X-API-Key": key})
    assert response.status_code == 200, response.text
    return dict(response.json())


def _enqueue_refresh(
    client: TestClient[Litestar], key: str, catalogue_id: uuid.UUID, *, input_key: str
) -> tuple[int, dict[str, object]]:
    """Enqueue a fetch_url of the portal page under ``input_key`` through the machine enqueue route; return the status and JSON answer."""
    body = {
        "catalogue_service_id": str(catalogue_id),
        "kind": "fetch_url",
        "target_url": PAGE_URL,
        "input_key": input_key,
    }
    response = client.post(ENQUEUE_URL, json=body, headers={"X-API-Key": key})
    assert response.status_code in (200, 201), response.text
    return response.status_code, dict(response.json())


def _week_tasks(session: Session, catalogue_id: uuid.UUID, input_key: str) -> list[DiscoveryTask]:
    """Return the fetch_url tasks of one catalogue row under ``input_key``."""
    stmt = select(DiscoveryTask).where(
        DiscoveryTask.catalogue_service_id == catalogue_id,
        DiscoveryTask.kind == DiscoveryTaskKind.FETCH_URL,
        DiscoveryTask.input_key == input_key,
    )
    return list(session.scalars(stmt).all())


def test_a_page_fetched_before_the_refresh_age_is_listed_under_this_weeks_key(
    machine_client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
) -> None:
    """catalogue refresh · happy: a page whose newest fetch is 31 days old is listed once, with this week's refresh key."""
    catalogue_id, _ = _page(db_session, "svc-stale", fetched_days_ago=31)
    key = _issue_key(db_session)

    answer = _stale(machine_client, key)

    assert answer["input_key"] == refresh_key(datetime.now(UTC))
    items = answer["items"]
    assert isinstance(items, list)
    assert [(item["catalogue_service_id"], item["target_url"]) for item in items] == [(str(catalogue_id), PAGE_URL)]


def test_a_page_fetched_within_the_refresh_age_is_not_listed(
    machine_client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
) -> None:
    """catalogue refresh · negative: a page fetched a day ago is fresh, so the listing is empty."""
    _page(db_session, "svc-fresh", fetched_days_ago=1)
    key = _issue_key(db_session)

    assert _stale(machine_client, key)["items"] == []


def test_a_page_with_an_open_fetch_task_is_not_listed(
    machine_client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
) -> None:
    """catalogue refresh · negative: a stale page that already has a pending fetch_url is skipped, so the step is idempotent."""
    catalogue_id, _ = _page(db_session, "svc-open", fetched_days_ago=40)
    open_task = DiscoveryRepository(db_session).insert_task(_page_target(catalogue_id, input_key="rr:2026-W01"))
    assert open_task.status is DiscoveryTaskStatus.PENDING
    key = _issue_key(db_session)

    assert _stale(machine_client, key)["items"] == []


def test_a_page_that_was_never_fetched_is_not_listed(
    machine_client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
) -> None:
    """catalogue refresh · negative: a page with no fetch logged has no age to exceed, so it is left to the ingest path."""
    _page(db_session, "svc-unfetched", fetched_days_ago=None)
    key = _issue_key(db_session)

    assert _stale(machine_client, key)["items"] == []


def test_the_listing_is_bounded_by_its_limit_and_takes_the_stalest_first(
    machine_client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
) -> None:
    """catalogue refresh · negative: three stale pages and a limit of two list the two oldest fetches, oldest first."""
    oldest, _ = _page(db_session, "svc-40", fetched_days_ago=40)
    middle, _ = _page(db_session, "svc-35", fetched_days_ago=35)
    _page(db_session, "svc-31", fetched_days_ago=31)
    key = _issue_key(db_session)

    items = _stale(machine_client, key, limit=2)["items"]

    assert isinstance(items, list)
    assert [item["catalogue_service_id"] for item in items] == [str(oldest), str(middle)]


def test_a_refresh_fetch_is_enqueued_once_under_the_week_key(
    machine_client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
) -> None:
    """catalogue refresh · happy: the first enqueue of a stale page under this week's key creates one pending fetch_url."""
    catalogue_id, _ = _page(db_session, "svc-enqueue", fetched_days_ago=40)
    key = _issue_key(db_session)
    week_key = refresh_key(datetime.now(UTC))

    status, answer = _enqueue_refresh(machine_client, key, catalogue_id, input_key=week_key)

    assert status == 201 and answer["created"] is True
    assert [task.status for task in _week_tasks(db_session, catalogue_id, week_key)] == [DiscoveryTaskStatus.PENDING]


def test_a_second_refresh_enqueue_in_the_same_week_creates_no_task(
    machine_client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
) -> None:
    """catalogue refresh · negative: a repeat enqueue under the same key answers created false and adds no row."""
    catalogue_id, _ = _page(db_session, "svc-repeat", fetched_days_ago=40)
    key = _issue_key(db_session)
    week_key = refresh_key(datetime.now(UTC))
    _enqueue_refresh(machine_client, key, catalogue_id, input_key=week_key)

    status, answer = _enqueue_refresh(machine_client, key, catalogue_id, input_key=week_key)

    assert status == 200 and answer["created"] is False
    assert len(_week_tasks(db_session, catalogue_id, week_key)) == 1


def test_a_refresh_fetch_with_a_changed_body_renders_under_this_weeks_key(
    machine_client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
) -> None:
    """catalogue refresh · happy: a refresh fetch whose body differs from the page's last body is due a render, keyed by the week."""
    key = _issue_key(db_session)
    catalogue_id, base_id = _page(db_session, "svc-changed", fetched_days_ago=None)
    _fetch(machine_client, key, base_id, body_sha256=HASH_A, final_url=PAGE_URL)
    _completed_render(db_session, catalogue_id, updated_at=datetime.now(UTC) - timedelta(days=1))
    week_key = refresh_key(datetime.now(UTC))
    refresh = DiscoveryRepository(db_session).insert_task(_page_target(catalogue_id, input_key=week_key))

    answer = _fetch(machine_client, key, refresh.id, body_sha256=HASH_B, final_url=PAGE_URL)

    assert answer["render_due"] is True
    assert answer["render_input_key"] == week_key


def test_a_refresh_fetch_with_an_unchanged_body_renders_nothing(
    machine_client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
) -> None:
    """catalogue refresh · negative: the refresh task is new, but its body matches the page's last fetch and the render is fresh, so no render."""
    key = _issue_key(db_session)
    catalogue_id, base_id = _page(db_session, "svc-unchanged", fetched_days_ago=None)
    _fetch(machine_client, key, base_id, body_sha256=HASH_A, final_url=PAGE_URL)
    _completed_render(db_session, catalogue_id, updated_at=datetime.now(UTC) - timedelta(days=1))
    week_key = refresh_key(datetime.now(UTC))
    refresh = DiscoveryRepository(db_session).insert_task(_page_target(catalogue_id, input_key=week_key))

    answer = _fetch(machine_client, key, refresh.id, body_sha256=HASH_A, final_url=PAGE_URL)

    assert answer["render_due"] is False
