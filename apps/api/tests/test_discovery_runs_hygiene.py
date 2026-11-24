"""Run hygiene on the machine run routes: a run that never got its finish is closed when the next run starts."""

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
from app.models.discovery import DiscoveryRunKind, DiscoveryRunStage, DiscoveryRunStatus
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy.orm import Session

RUNS_URL = "/api/v1/discovery/machine/runs"
STALE_DETAIL = "stale: no finish received"


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


def _open_run(db_session: Session, started_at: datetime) -> str:
    """Insert a ``running`` worker-drain run that started at ``started_at``, as an earlier process left it."""
    run = DiscoveryRepository(db_session).insert_run(
        DiscoveryRunKind.WORKER_DRAIN, DiscoveryRunStage.WORKER_DRAIN, started_at=started_at
    )
    db_session.flush()
    return str(run.id)


def _status_of(db_session: Session, run_id: str) -> DiscoveryRunStatus:
    db_session.expire_all()
    run = DiscoveryRepository(db_session).get_run(uuid.UUID(run_id))
    assert run is not None
    return DiscoveryRunStatus(run.status)


def test_a_stale_run_is_closed_as_failed_when_a_run_starts(
    client: TestClient[Litestar], db_session: Session, headers: dict[str, str]
) -> None:
    """stale · a run older than an hour, never finished, is closed as failed with the stale reason; the new run is recorded."""
    stale_id = _open_run(db_session, datetime.now(UTC) - timedelta(hours=2))

    response = client.post(RUNS_URL, json={"kind": "worker_drain"}, headers=headers)

    assert response.status_code == 201
    assert response.json()["status"] == "running"
    assert _status_of(db_session, stale_id) == DiscoveryRunStatus.FAILED
    stale = DiscoveryRepository(db_session).get_run(uuid.UUID(stale_id))
    assert stale is not None
    assert stale.error_detail == STALE_DETAIL and stale.finished_at is not None


def test_a_fresh_run_is_left_alone_when_another_run_starts(
    client: TestClient[Litestar], db_session: Session, headers: dict[str, str]
) -> None:
    """stale · a run younger than an hour is still in progress and stays running."""
    fresh_id = _open_run(db_session, datetime.now(UTC) - timedelta(minutes=10))

    client.post(RUNS_URL, json={"kind": "worker_drain"}, headers=headers)

    assert _status_of(db_session, fresh_id) == DiscoveryRunStatus.RUNNING


def test_a_run_closed_as_stale_refuses_a_late_finish(
    client: TestClient[Litestar], db_session: Session, headers: dict[str, str]
) -> None:
    """stale · the finish that arrives after the sweep is refused, so the stale record stays as it was closed."""
    stale_id = _open_run(db_session, datetime.now(UTC) - timedelta(hours=2))
    client.post(RUNS_URL, json={"kind": "worker_drain"}, headers=headers)

    late = client.post(
        f"{RUNS_URL}/{stale_id}/finish",
        json={
            "status": "succeeded",
            "claimed_count": 1,
            "completed_count": 1,
            "failed_count": 0,
            "skipped_count": 0,
            "stop_reason": "queue_empty",
        },
        headers=headers,
    )

    assert late.status_code == 422
    assert _status_of(db_session, stale_id) == DiscoveryRunStatus.FAILED
