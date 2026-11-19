"""Change detection on fetched bodies: the fetch log keeps the body hash, and the verdict renders only what changed or aged out."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.features.discovery.render_gate import RenderHistory, decide_render
from app.features.discovery.repository import DiscoveryRepository, TaskTarget
from app.models.discovery import DiscoveryFetchLog, DiscoveryTask, DiscoveryTaskKind, DiscoveryTaskStatus
from litestar import Litestar
from litestar.testing import TestClient
from pydantic import JsonValue
from sqlalchemy import select
from sqlalchemy.orm import Session

from test_discovery_admin_api import _catalogue
from test_discovery_machine_api import _issue_key
from test_discovery_machine_api import client as machine_client  # noqa: F401

NOW = datetime(2026, 11, 19, 12, 0, tzinfo=UTC)
MAX_AGE = timedelta(days=30)
HASH_A = "a" * 64
HASH_B = "b" * 64
PAGE_URL = "https://portal.example/service/1"
FETCHES_URL = "/api/v1/discovery/machine/tasks/{task_id}/fetches"


def _history(last_completed_at: datetime | None) -> RenderHistory:
    """Return the render history of a page whose last finished render was at ``last_completed_at``."""
    return RenderHistory(last_completed_at=last_completed_at)


def test_an_unchanged_body_enqueues_no_render() -> None:
    """render gate · negative: the same body hash, with a render finished 1 day ago, enqueues nothing."""
    verdict = decide_render(
        previous_sha256=HASH_A,
        body_sha256=HASH_A,
        history=_history(NOW - timedelta(days=1)),
        now=NOW,
        max_age=MAX_AGE,
    )

    assert verdict.due is False


def test_a_changed_body_enqueues_a_render() -> None:
    """render gate · happy: a body whose hash differs from the last stored one is due a render."""
    verdict = decide_render(
        previous_sha256=HASH_A,
        body_sha256=HASH_B,
        history=_history(NOW - timedelta(days=1)),
        now=NOW,
        max_age=MAX_AGE,
    )

    assert verdict.due is True


def test_a_page_older_than_the_refresh_age_is_re_rendered_when_unchanged() -> None:
    """render gate · happy: an unchanged body is still due a render when the last render is older than the refresh age."""
    verdict = decide_render(
        previous_sha256=HASH_A,
        body_sha256=HASH_A,
        history=_history(NOW - timedelta(days=31)),
        now=NOW,
        max_age=MAX_AGE,
    )

    assert verdict.due is True


def test_a_page_that_was_never_rendered_is_rendered_even_when_unchanged() -> None:
    """render gate · happy: a page with no finished render has no age to wait for, so it is rendered."""
    verdict = decide_render(
        previous_sha256=HASH_A, body_sha256=HASH_A, history=_history(None), now=NOW, max_age=MAX_AGE
    )

    assert verdict.due is True


def _fetch_task(session: Session, catalogue_id: uuid.UUID) -> DiscoveryTask:
    """Insert a fetch_url task for the portal page."""
    target = TaskTarget(catalogue_service_id=catalogue_id, kind=DiscoveryTaskKind.FETCH_URL, target_url=PAGE_URL)
    return DiscoveryRepository(session).insert_task(target)


def _fetch(
    http: TestClient[Litestar],
    key: str,
    task_id: uuid.UUID,
    *,
    body_sha256: str | None = None,
    final_url: str | None = None,
) -> dict[str, JsonValue]:
    """POST one successful HTML fetch-log entry for ``task_id`` with its body hash and final url; return the JSON answer."""
    payload: dict[str, str | int | None] = {
        "http_status": 200,
        "content_type": "text/html",
        "byte_length": 10,
        "body_sha256": body_sha256,
        "final_url": final_url,
    }
    response = http.post(FETCHES_URL.format(task_id=task_id), json=payload, headers={"X-API-Key": key})
    assert response.status_code == 201, response.text
    return dict(response.json())


def test_the_fetch_log_keeps_the_body_hash_and_asks_for_the_first_render(
    machine_client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
) -> None:
    """render gate · happy: the fetch row stores the body hash, and the first body of a page asks for a render."""
    catalogue = _catalogue(db_session)
    task = _fetch_task(db_session, catalogue.id)
    key = _issue_key(db_session)

    answer = _fetch(machine_client, key, task.id, body_sha256=HASH_A, final_url=PAGE_URL)

    assert answer["render_due"] is True and answer["render_input_key"] is None
    stored = db_session.scalars(select(DiscoveryFetchLog).where(DiscoveryFetchLog.discovery_task_id == task.id)).one()
    assert stored.body_sha256 == HASH_A


def test_a_body_hash_that_is_not_sha256_hex_is_rejected_and_nothing_is_logged(
    machine_client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
) -> None:
    """render gate · negative: a hash that is not 64 lowercase hex characters is refused and writes no fetch row."""
    catalogue = _catalogue(db_session)
    task = _fetch_task(db_session, catalogue.id)
    key = _issue_key(db_session)

    response = machine_client.post(
        FETCHES_URL.format(task_id=task.id),
        json={"http_status": 200, "body_sha256": "not-a-hash", "final_url": PAGE_URL},
        headers={"X-API-Key": key},
    )

    assert response.status_code == 422
    assert (
        db_session.scalars(select(DiscoveryFetchLog).where(DiscoveryFetchLog.discovery_task_id == task.id)).all() == []
    )


def test_an_unchanged_body_enqueues_no_render_through_the_fetch_route(
    machine_client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
) -> None:
    """render gate · negative: a second fetch with the same hash, after a render finished yesterday, asks for no render."""
    catalogue = _catalogue(db_session)
    task = _fetch_task(db_session, catalogue.id)
    key = _issue_key(db_session)
    _fetch(machine_client, key, task.id, body_sha256=HASH_A, final_url=PAGE_URL)
    _completed_render(db_session, catalogue.id, updated_at=datetime.now(UTC) - timedelta(days=1))

    answer = _fetch(machine_client, key, task.id, body_sha256=HASH_A, final_url=PAGE_URL)

    assert answer["render_due"] is False


def _completed_render(session: Session, catalogue_id: uuid.UUID, *, updated_at: datetime) -> None:
    """Insert a completed render_page for the portal page, finished at ``updated_at``."""
    target = TaskTarget(catalogue_service_id=catalogue_id, kind=DiscoveryTaskKind.RENDER_PAGE, target_url=PAGE_URL)
    task = DiscoveryRepository(session).insert_task(target)
    task.status = DiscoveryTaskStatus.COMPLETED
    task.updated_at = updated_at
    session.flush()


def test_a_worker_without_a_body_hash_is_logged_and_asks_for_no_render(
    machine_client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
) -> None:
    """render gate · happy: a fetch from a worker that predates the hash is logged, and it asks for no render."""
    catalogue = _catalogue(db_session)
    task = _fetch_task(db_session, catalogue.id)
    key = _issue_key(db_session)

    answer = _fetch(machine_client, key, task.id)

    assert answer["render_due"] is False
    stored = db_session.scalars(select(DiscoveryFetchLog).where(DiscoveryFetchLog.discovery_task_id == task.id)).one()
    assert stored.body_sha256 is None


def test_the_first_hashed_fetch_after_a_hashless_one_is_due_a_render(
    machine_client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
) -> None:
    """render gate · negative: with no stored hash to match, the first hashed body of a page counts as changed."""
    catalogue = _catalogue(db_session)
    task = _fetch_task(db_session, catalogue.id)
    key = _issue_key(db_session)
    _fetch(machine_client, key, task.id)

    answer = _fetch(machine_client, key, task.id, body_sha256=HASH_A, final_url=PAGE_URL)

    assert answer["render_due"] is True
