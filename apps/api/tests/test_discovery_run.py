"""Worker-run lifecycle over the discovery machine API (queue observability)."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import app.features.auth.guard_session as guard_session_module
import pytest
from app.config import settings
from app.features.auth.repository import ApiKeyRepository
from app.features.auth.service import ApiKeyService
from app.features.discovery.repository import DiscoveryRepository
from app.main import create_app
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy.orm import Session

RUNS_URL = "/api/v1/discovery/machine/runs"


@contextmanager
def _keep_open(session: Session) -> Iterator[Session]:
    yield session


@pytest.fixture
def client(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient[Litestar]]:
    monkeypatch.setattr(settings, "discovery_machine_opt_in", True)
    monkeypatch.setattr(guard_session_module, "SessionLocal", lambda: _keep_open(db_session))
    monkeypatch.setattr("app.main.provide_session", lambda: db_session)
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def headers(db_session: Session) -> dict[str, str]:
    service = ApiKeyService(ApiKeyRepository(db_session))
    key = service.issue("discovery-ingest")
    service.verify(key)
    db_session.flush()
    return {"X-API-Key": key}


def _start(client: TestClient[Litestar], headers: dict[str, str]) -> str:
    response = client.post(RUNS_URL, json={"kind": "worker_drain"}, headers=headers)
    assert response.status_code == 201
    assert response.json()["status"] == "running"
    return str(response.json()["id"])


def _finish_body(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "status": "succeeded",
        "claimed_count": 3,
        "completed_count": 2,
        "failed_count": 1,
        "skipped_count": 0,
        "remaining_count": None,
        "stop_reason": "queue_empty",
    }
    body.update(overrides)
    return body


def test_worker_run_lifecycle_records_a_successful_bounded_run(
    client: TestClient[Litestar], db_session: Session, headers: dict[str, str]
) -> None:
    run_id = _start(client, headers)

    response = client.post(f"{RUNS_URL}/{run_id}/finish", json=_finish_body(), headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "succeeded"
    latest = DiscoveryRepository(db_session).latest_successful_run()
    assert latest is not None
    assert str(latest.id) == run_id
    assert (latest.claimed_count, latest.completed_count, latest.failed_count) == (3, 2, 1)
    assert latest.stop_reason == "queue_empty"
    assert latest.finished_at is not None


def test_failed_or_interrupted_run_is_not_reported_as_last_successful(
    client: TestClient[Litestar], db_session: Session, headers: dict[str, str]
) -> None:
    good_id = _start(client, headers)
    client.post(f"{RUNS_URL}/{good_id}/finish", json=_finish_body(), headers=headers)
    failed_id = _start(client, headers)
    failed = _finish_body(status="failed", stop_reason="error", error_detail="boom")
    client.post(f"{RUNS_URL}/{failed_id}/finish", json=failed, headers=headers)
    _start(client, headers)

    latest = DiscoveryRepository(db_session).latest_successful_run()

    assert latest is not None
    assert str(latest.id) == good_id


def test_stale_running_run_is_counted_from_its_age(
    client: TestClient[Litestar], db_session: Session, headers: dict[str, str]
) -> None:
    _start(client, headers)
    repo = DiscoveryRepository(db_session)
    now = datetime.now(UTC)

    assert repo.count_stale_runs(now=now) == 0
    assert repo.count_stale_runs(now=now + timedelta(hours=2)) == 1


def test_finish_unknown_run_returns_404(client: TestClient[Litestar], headers: dict[str, str]) -> None:
    response = client.post(f"{RUNS_URL}/{uuid.uuid4()}/finish", json=_finish_body(), headers=headers)

    assert response.status_code == 404


def test_finish_already_finished_run_returns_422(client: TestClient[Litestar], headers: dict[str, str]) -> None:
    run_id = _start(client, headers)
    client.post(f"{RUNS_URL}/{run_id}/finish", json=_finish_body(), headers=headers)

    response = client.post(f"{RUNS_URL}/{run_id}/finish", json=_finish_body(), headers=headers)

    assert response.status_code == 422


def test_finish_with_running_status_is_rejected_and_run_requires_api_key(
    client: TestClient[Litestar], headers: dict[str, str]
) -> None:
    run_id = _start(client, headers)

    bad_status = client.post(f"{RUNS_URL}/{run_id}/finish", json=_finish_body(status="running"), headers=headers)
    anonymous = client.post(RUNS_URL, json={"kind": "worker_drain"})

    assert bad_status.status_code == 422
    assert anonymous.status_code == 401


@pytest.mark.parametrize(
    "reason", ["browser_budget", "browser_quota", "storage_unavailable", "db_limit", "llm_budget", "llm_quota"]
)
def test_finish_records_the_stop_reasons_of_a_run_that_hit_a_free_allocation(
    client: TestClient[Litestar], db_session: Session, headers: dict[str, str], reason: str
) -> None:
    run_id = _start(client, headers)

    response = client.post(f"{RUNS_URL}/{run_id}/finish", json=_finish_body(stop_reason=reason), headers=headers)

    assert response.status_code == 200
    latest = DiscoveryRepository(db_session).latest_successful_run()
    assert latest is not None and latest.stop_reason == reason


def test_finish_rejects_a_stop_reason_the_worker_does_not_define(
    client: TestClient[Litestar], headers: dict[str, str]
) -> None:
    run_id = _start(client, headers)

    response = client.post(
        f"{RUNS_URL}/{run_id}/finish", json=_finish_body(stop_reason="coffee_break"), headers=headers
    )

    assert response.status_code == 422
