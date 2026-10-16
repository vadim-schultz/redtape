"""HTTP behavior of discovery machine routes (chapter 3)."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import app.features.auth.guards as auth_guards
import pytest
from app.config import settings
from app.features.auth.repository import ApiKeyRepository
from app.features.auth.service import ApiKeyService
from app.main import create_app
from app.models.discovery import (
    DiscoveryEvent,
    DiscoveryEventType,
    DiscoveryFetchLog,
    DiscoveryTask,
    DiscoveryTaskKind,
    DiscoveryTaskStatus,
)
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

BATCH_URL = "/api/v1/discovery/machine/catalogue/batch"
CLAIM_URL = "/api/v1/discovery/machine/tasks/claim"


@contextmanager
def _keep_open(session: Session) -> Iterator[Session]:
    yield session


@pytest.fixture
def client(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient[Litestar]]:
    monkeypatch.setattr(settings, "discovery_machine_opt_in", True)
    monkeypatch.setattr(auth_guards, "SessionLocal", lambda: _keep_open(db_session))
    monkeypatch.setattr("app.main.provide_session", lambda: db_session)
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def country(db_session: Session) -> Jurisdiction:
    jurisdiction = Jurisdiction(
        kind=JurisdictionKind.COUNTRY,
        name_i18n={"en": "Testland"},
        code=f"T{uuid.uuid4().hex[:8]}",
    )
    db_session.add(jurisdiction)
    db_session.flush()
    return jurisdiction


def _issue_key(db_session: Session) -> str:
    service = ApiKeyService(ApiKeyRepository(db_session))
    key = service.issue("discovery-ingest")
    service.verify(key)
    db_session.flush()
    return key


def _batch_item(country: Jurisdiction, **overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "source": "govdata",
        "external_id": "svc-42",
        "jurisdiction_id": str(country.id),
        "title_i18n": {"de": "Leistung"},
        "portal_url": "https://example.gov/service",
        "raw_payload": {"id": "svc-42"},
    }
    body.update(overrides)
    return body


def test_post_catalogue_batch_upserts_row_and_creates_pending_fetch_task_when_portal_url_set(
    client: TestClient[Litestar],
    db_session: Session,
    country: Jurisdiction,
) -> None:
    key = _issue_key(db_session)
    response = client.post(
        BATCH_URL,
        json={"items": [_batch_item(country)]},
        headers={"X-API-Key": key},
    )

    assert response.status_code == 201
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["external_id"] == "svc-42"
    assert body["items"][0]["task_id"] is not None

    task_id = uuid.UUID(body["items"][0]["task_id"])
    task = db_session.get(DiscoveryTask, task_id)
    assert task is not None
    assert task.kind == DiscoveryTaskKind.FETCH_URL
    assert task.status == DiscoveryTaskStatus.PENDING
    assert task.target_url == "https://example.gov/service"

    events = list(
        db_session.scalars(
            select(DiscoveryEvent).where(DiscoveryEvent.event_type == DiscoveryEventType.CATALOGUE_UPSERTED)
        )
    )
    assert len(events) == 1
    enqueued = list(
        db_session.scalars(select(DiscoveryEvent).where(DiscoveryEvent.event_type == DiscoveryEventType.TASK_ENQUEUED))
    )
    assert len(enqueued) == 1


def test_post_catalogue_batch_returns_401_without_api_key(
    client: TestClient[Litestar],
    country: Jurisdiction,
) -> None:
    response = client.post(BATCH_URL, json={"items": [_batch_item(country)]})

    assert response.status_code == 401


def test_post_catalogue_batch_returns_422_for_missing_external_id(
    client: TestClient[Litestar],
    db_session: Session,
    country: Jurisdiction,
) -> None:
    key = _issue_key(db_session)
    item = _batch_item(country)
    del item["external_id"]
    response = client.post(BATCH_URL, json={"items": [item]}, headers={"X-API-Key": key})

    assert response.status_code == 422


def test_post_tasks_claim_assigns_pending_tasks_to_the_caller_key(
    client: TestClient[Litestar],
    db_session: Session,
    country: Jurisdiction,
) -> None:
    key = _issue_key(db_session)
    batch = client.post(
        BATCH_URL,
        json={"items": [_batch_item(country, external_id="claim-me")]},
        headers={"X-API-Key": key},
    )
    assert batch.status_code == 201
    task_id = uuid.UUID(batch.json()["items"][0]["task_id"])

    claim = client.post(CLAIM_URL, json={"limit": 1}, headers={"X-API-Key": key})

    assert claim.status_code == 200
    items = claim.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == str(task_id)
    assert items[0]["status"] == "claimed"
    assert items[0]["lease_expires_at"] is not None

    task = db_session.get(DiscoveryTask, task_id)
    assert task is not None
    assert task.status == DiscoveryTaskStatus.CLAIMED
    assert task.claimed_by_api_key_id is not None


def test_post_tasks_claim_returns_empty_list_when_queue_drained(
    client: TestClient[Litestar],
    db_session: Session,
) -> None:
    key = _issue_key(db_session)
    response = client.post(CLAIM_URL, json={"limit": 5}, headers={"X-API-Key": key})

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_post_tasks_claim_reclaims_expired_claimed_task(
    client: TestClient[Litestar],
    db_session: Session,
    country: Jurisdiction,
) -> None:
    key = _issue_key(db_session)
    batch = client.post(
        BATCH_URL,
        json={"items": [_batch_item(country, external_id="lease-expired")]},
        headers={"X-API-Key": key},
    )
    assert batch.status_code == 201
    task_id = uuid.UUID(batch.json()["items"][0]["task_id"])

    first_claim = client.post(CLAIM_URL, json={"limit": 1}, headers={"X-API-Key": key})
    assert first_claim.status_code == 200
    assert len(first_claim.json()["items"]) == 1

    task = db_session.get(DiscoveryTask, task_id)
    assert task is not None
    task.lease_expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.flush()

    second_claim = client.post(CLAIM_URL, json={"limit": 1}, headers={"X-API-Key": key})

    assert second_claim.status_code == 200
    items = second_claim.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == str(task_id)
    assert items[0]["status"] == "claimed"

    db_session.refresh(task)
    assert task.status == DiscoveryTaskStatus.CLAIMED
    assert task.claimed_by_api_key_id is not None
    assert task.lease_expires_at is not None
    assert task.lease_expires_at > datetime.now(UTC)


def test_post_tasks_claim_does_not_reclaim_task_with_future_lease(
    client: TestClient[Litestar],
    db_session: Session,
    country: Jurisdiction,
) -> None:
    key = _issue_key(db_session)
    batch = client.post(
        BATCH_URL,
        json={"items": [_batch_item(country, external_id="lease-active")]},
        headers={"X-API-Key": key},
    )
    assert batch.status_code == 201
    task_id = uuid.UUID(batch.json()["items"][0]["task_id"])

    first_claim = client.post(CLAIM_URL, json={"limit": 1}, headers={"X-API-Key": key})
    assert first_claim.status_code == 200
    assert len(first_claim.json()["items"]) == 1

    task = db_session.get(DiscoveryTask, task_id)
    assert task is not None
    task.lease_expires_at = datetime.now(UTC) + timedelta(hours=1)
    db_session.flush()

    second_claim = client.post(CLAIM_URL, json={"limit": 1}, headers={"X-API-Key": key})

    assert second_claim.status_code == 200
    assert second_claim.json()["items"] == []

    db_session.refresh(task)
    assert task.status == DiscoveryTaskStatus.CLAIMED


def test_post_tasks_fetches_appends_fetch_log_and_leaves_task_claimed(
    client: TestClient[Litestar],
    db_session: Session,
    country: Jurisdiction,
) -> None:
    key = _issue_key(db_session)
    batch = client.post(
        BATCH_URL,
        json={"items": [_batch_item(country, external_id="fetch-me")]},
        headers={"X-API-Key": key},
    )
    task_id = uuid.UUID(batch.json()["items"][0]["task_id"])
    client.post(CLAIM_URL, json={"limit": 1}, headers={"X-API-Key": key})

    fetches_url = f"/api/v1/discovery/machine/tasks/{task_id}/fetches"
    response = client.post(
        fetches_url,
        json={"http_status": 200, "content_type": "text/html", "byte_length": 1024},
        headers={"X-API-Key": key},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["task_status"] == "claimed"

    task = db_session.get(DiscoveryTask, task_id)
    assert task is not None
    assert task.status == DiscoveryTaskStatus.CLAIMED

    logs = list(db_session.scalars(select(DiscoveryFetchLog).where(DiscoveryFetchLog.discovery_task_id == task_id)))
    assert len(logs) == 1
    assert logs[0].http_status == 200
