"""Epoch keys for refresh renders: a page that was rendered is refreshed under its week's key, so a finished render never blocks the next week."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.features.discovery.render_gate import RenderHistory, decide_render
from app.features.discovery.repository import DiscoveryRepository, TaskTarget
from app.models.discovery import DiscoveryTaskKind, DiscoveryTaskStatus
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy.orm import Session

from test_discovery_admin_api import _catalogue
from test_discovery_machine_api import _issue_key
from test_discovery_machine_api import client as machine_client  # noqa: F401

PAGE_URL = "https://portal.example/service/1"
HASH_A = "a" * 64
HASH_B = "b" * 64
MAX_AGE = timedelta(days=30)
WEEK_46 = datetime(2026, 11, 12, 12, tzinfo=UTC)
WEEK_47 = datetime(2026, 11, 19, 12, tzinfo=UTC)
TASKS_URL = "/api/v1/discovery/machine/tasks"


def _completed_render(
    session: Session, catalogue_id: uuid.UUID, *, input_key: str | None, finished_at: datetime
) -> None:
    """Insert a completed render_page for the portal page under ``input_key``, finished at ``finished_at``."""
    target = TaskTarget(
        catalogue_service_id=catalogue_id,
        kind=DiscoveryTaskKind.RENDER_PAGE,
        target_url=PAGE_URL,
        input_key=input_key,
    )
    task = DiscoveryRepository(session).insert_task(target)
    task.status = DiscoveryTaskStatus.COMPLETED
    task.updated_at = finished_at
    session.flush()


def _enqueue_render(http: TestClient[Litestar], key: str, catalogue_id: uuid.UUID, input_key: str) -> dict[str, object]:
    """Enqueue the render of the portal page under ``input_key`` and return the JSON answer."""
    body = {
        "catalogue_service_id": str(catalogue_id),
        "kind": "render_page",
        "target_url": PAGE_URL,
        "input_key": input_key,
    }
    response = http.post(TASKS_URL, json=body, headers={"X-API-Key": key})
    assert response.status_code in (200, 201), response.text
    return dict(response.json())


def test_a_refresh_render_does_not_block_the_next_weeks_refresh() -> None:
    """render epoch · happy: a page rendered in week 46 and changed in week 47 is due a render under the week 47 key."""
    verdict = decide_render(
        previous_sha256=HASH_A,
        body_sha256=HASH_B,
        history=RenderHistory(last_completed_at=WEEK_46),
        now=WEEK_47,
        max_age=MAX_AGE,
    )

    assert verdict.due is True
    assert verdict.input_key == "rr:2026-W47"


def test_an_aged_page_is_refreshed_under_the_key_of_its_week() -> None:
    """render epoch · happy: an unchanged page whose last render is past the refresh age is refreshed under this week's key."""
    verdict = decide_render(
        previous_sha256=HASH_A,
        body_sha256=HASH_A,
        history=RenderHistory(last_completed_at=WEEK_46 - timedelta(days=30)),
        now=WEEK_47,
        max_age=MAX_AGE,
    )

    assert verdict.due is True
    assert verdict.input_key == "rr:2026-W47"


def test_a_new_page_keeps_the_empty_input_key() -> None:
    """render epoch · negative: a page with no finished render gets the empty key, the identity first renders always had."""
    verdict = decide_render(
        previous_sha256=HASH_A,
        body_sha256=HASH_B,
        history=RenderHistory(last_completed_at=None),
        now=WEEK_47,
        max_age=MAX_AGE,
    )

    assert verdict.due is True
    assert verdict.input_key is None


def test_a_completed_week_46_refresh_does_not_block_the_week_47_enqueue(
    machine_client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
) -> None:
    """render epoch · happy: a completed refresh keyed by week 46 does not stop the week 47 render of the same page."""
    catalogue = _catalogue(db_session)
    _completed_render(db_session, catalogue.id, input_key="rr:2026-W46", finished_at=WEEK_46)
    key = _issue_key(db_session)

    answer = _enqueue_render(machine_client, key, catalogue.id, "rr:2026-W47")

    assert answer["created"] is True


def test_a_second_refresh_in_the_same_week_is_not_a_second_render(
    machine_client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
) -> None:
    """render epoch · negative: the week 47 refresh already finished, so another enqueue for week 47 creates nothing."""
    catalogue = _catalogue(db_session)
    _completed_render(db_session, catalogue.id, input_key="rr:2026-W47", finished_at=WEEK_47)
    key = _issue_key(db_session)

    answer = _enqueue_render(machine_client, key, catalogue.id, "rr:2026-W47")

    assert answer["created"] is False
