"""The database soft limit on machine write routes (chapter 23)."""

from __future__ import annotations

import logging
import uuid

import app.features.discovery.db_headroom as headroom_module
import pytest
from app.config import Settings, settings
from app.features.discovery.db_headroom import DatabaseHeadroom, DatabaseSoftLimitError, read_database_size
from app.models.discovery import DiscoveryTaskKind
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from test_discovery_admin_api import _catalogue, _kind_task
from test_discovery_machine_api import _issue_key

MACHINE = "/api/v1/discovery/machine"
LIMIT = 1000


class FakeClock:
    """A monotonic clock the test moves by hand."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class SizeProbe:
    """Stands in for the size query: returns a settable size and counts reads."""

    def __init__(self, size: int) -> None:
        self.size = size
        self.reads = 0
        self.clock = FakeClock()

    def __call__(self) -> int:
        self.reads += 1
        return self.size

    def change_to(self, size: int) -> None:
        """Set a new size and let the cache lapse so the next request measures it."""
        self.size = size
        self.clock.now += 301.0


def _headroom(probe: SizeProbe, clock: FakeClock | None = None) -> DatabaseHeadroom:
    return DatabaseHeadroom(read_size=probe, clock=clock or probe.clock, limit=lambda: LIMIT)


def test_ensure_room_raises_above_the_limit_and_passes_at_or_below_it() -> None:
    _headroom(SizeProbe(LIMIT)).ensure_room()
    _headroom(SizeProbe(LIMIT - 1)).ensure_room()

    with pytest.raises(DatabaseSoftLimitError):
        _headroom(SizeProbe(LIMIT + 1)).ensure_room()


def test_the_size_is_read_at_most_once_per_five_minutes() -> None:
    probe, clock = SizeProbe(10), FakeClock()
    headroom = _headroom(probe, clock)

    headroom.ensure_room()
    clock.now = 299.0
    headroom.ensure_room()
    assert probe.reads == 1

    clock.now = 301.0
    probe.size = LIMIT + 1
    with pytest.raises(DatabaseSoftLimitError):
        headroom.ensure_room()
    assert probe.reads == 2


def test_a_failing_size_query_lets_the_request_through_and_logs_a_warning(caplog: pytest.LogCaptureFixture) -> None:
    attempts: list[int] = []

    def broken() -> int:
        attempts.append(1)
        raise OperationalError("SELECT", {}, ConnectionError("down"))

    headroom = DatabaseHeadroom(read_size=broken, clock=FakeClock(), limit=lambda: LIMIT)

    with caplog.at_level(logging.WARNING, logger=headroom_module.__name__):
        headroom.ensure_room()
        headroom.ensure_room()

    assert len(attempts) == 2
    assert "database size" in caplog.text


@pytest.fixture
def probe(monkeypatch: pytest.MonkeyPatch) -> SizeProbe:
    """Route guards read the module-level headroom; point it at a probe with a tiny limit."""
    holder = SizeProbe(LIMIT - 1)
    monkeypatch.setattr(headroom_module, "db_headroom", _headroom(holder))
    return holder


def _enqueue_body(db_session: Session) -> dict[str, str]:
    catalogue = _catalogue(db_session, external_id="enq")
    return {"catalogue_service_id": str(catalogue.id), "kind": "fetch_url", "target_url": "https://example.gov/a"}


def test_a_write_route_answers_2xx_below_the_limit_and_507_database_soft_limit_above_it(
    client: TestClient[Litestar], db_session: Session, probe: SizeProbe
) -> None:
    headers = {"X-API-Key": _issue_key(db_session)}
    body = _enqueue_body(db_session)

    below = client.post(f"{MACHINE}/tasks", json=body, headers=headers)
    probe.change_to(LIMIT + 1)
    above = client.post(f"{MACHINE}/tasks", json={**body, "target_url": "https://example.gov/b"}, headers=headers)

    assert below.status_code == 201
    assert (above.status_code, above.json()["detail"]) == (507, "database_soft_limit")


def _claimed_fetch_task(client: TestClient[Litestar], db_session: Session, headers: dict[str, str]) -> str:
    _kind_task(
        db_session, _catalogue(db_session, external_id=f"svc-{uuid.uuid4().hex[:6]}"), DiscoveryTaskKind.FETCH_URL
    )
    claim = client.post(f"{MACHINE}/tasks/claim", json={"limit": 1, "kinds": ["fetch_url"]}, headers=headers)
    return str(claim.json()["items"][0]["id"])


def test_the_fetch_log_and_the_row_creating_posts_answer_507_above_the_limit(
    client: TestClient[Litestar], db_session: Session, probe: SizeProbe
) -> None:
    headers = {"X-API-Key": _issue_key(db_session)}
    task_id = _claimed_fetch_task(client, db_session, headers)
    probe.change_to(LIMIT + 1)
    guarded = [
        f"{MACHINE}/tasks/{task_id}/fetches",
        f"{MACHINE}/tasks/{task_id}/artifacts",
        f"{MACHINE}/entities",
        f"{MACHINE}/claims",
        f"{MACHINE}/candidates/mentions",
    ]

    statuses = [client.post(url, json={}, headers=headers).status_code for url in guarded]

    assert statuses == [507] * len(guarded)


def test_fetch_log_append_works_below_the_limit(
    client: TestClient[Litestar], db_session: Session, probe: SizeProbe
) -> None:
    headers = {"X-API-Key": _issue_key(db_session)}
    task_id = _claimed_fetch_task(client, db_session, headers)

    response = client.post(f"{MACHINE}/tasks/{task_id}/fetches", json={"http_status": 200}, headers=headers)

    assert response.status_code == 201


def test_complete_fail_release_claim_and_the_read_routes_still_work_above_the_limit(
    client: TestClient[Litestar], db_session: Session, probe: SizeProbe
) -> None:
    headers = {"X-API-Key": _issue_key(db_session)}
    first = _claimed_fetch_task(client, db_session, headers)
    second = _claimed_fetch_task(client, db_session, headers)
    third = _claimed_fetch_task(client, db_session, headers)
    probe.change_to(LIMIT + 1)

    released = client.post(f"{MACHINE}/tasks/{first}/release", json={"reason": "stopped"}, headers=headers)
    completed = client.post(f"{MACHINE}/tasks/{second}/complete", headers=headers)
    failed = client.post(f"{MACHINE}/tasks/{third}/fail", json={"error": "boom"}, headers=headers)
    reclaimed = client.post(f"{MACHINE}/tasks/claim", json={"limit": 1, "kinds": ["fetch_url"]}, headers=headers)
    reads = [
        client.get(f"{MACHINE}/{path}", headers=headers) for path in ("budgets", "tasks/summary", "artifacts/status")
    ]

    assert [r.status_code for r in (released, completed, failed, reclaimed)] == [200, 201, 201, 200]
    assert [r.status_code for r in reads] == [200, 200, 200]


def test_the_default_headroom_follows_the_configured_soft_limit() -> None:
    assert Settings(_env_file=None).db_soft_limit_bytes == 475_000_000
    assert DatabaseHeadroom().limit() == settings.db_soft_limit_bytes


def test_the_real_size_query_reports_the_current_database_in_bytes(db_session: Session) -> None:
    assert read_database_size() > 0
