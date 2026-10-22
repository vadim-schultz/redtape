"""HTTP and service tests for discovery machine emit to suggestions (chapter 18)."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager

import app.features.auth.guard_session as guard_session_module
import pytest
from app.config import settings
from app.features.auth.repository import ApiKeyRepository
from app.features.auth.service import ApiKeyService
from app.main import create_app
from app.models.discovery import (
    DiscoveryClaim,
    DiscoveryClaimKind,
    DiscoveryEntity,
    DiscoveryEvent,
    DiscoveryEventType,
)
from app.models.suggestion import Suggestion, SuggestionKind, SuggestionSource, SuggestionStatus
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from test_discovery_admin_api import _catalogue

EMIT_URL = "/api/v1/discovery/machine/catalogue/{catalogue_id}/emit"


@contextmanager
def _keep_open(session: Session) -> Iterator[Session]:
    yield session


@pytest.fixture
def client(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient[Litestar]]:
    monkeypatch.setattr(settings, "discovery_machine_opt_in", True)
    monkeypatch.setattr(guard_session_module, "SessionLocal", lambda: _keep_open(db_session))
    monkeypatch.setattr("app.main.provide_session", lambda: db_session)
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def _issue_key(db_session: Session) -> str:
    service = ApiKeyService(ApiKeyRepository(db_session))
    key = service.issue("discovery-emit")
    service.verify(key)
    db_session.flush()
    return key


def _new_document_claim(db_session: Session, catalogue_id: uuid.UUID) -> DiscoveryClaim:
    entity = DiscoveryEntity(
        catalogue_service_id=catalogue_id,
        canonical_url="https://example.gov/doc",
        label="Doc",
    )
    db_session.add(entity)
    db_session.flush()
    claim = DiscoveryClaim(
        discovery_entity_id=entity.id,
        kind=DiscoveryClaimKind.NEW_DOCUMENT,
        payload={
            "title_i18n": {"de": "Ausweis"},
            "official_url": "https://example.gov/doc",
        },
        payload_fingerprint="emit-test-doc-fp",
    )
    db_session.add(claim)
    db_session.flush()
    return claim


def test_emit_creates_pending_new_document_suggestion_for_emit_ready_claim(
    client: TestClient[Litestar], db_session: Session
) -> None:
    catalogue = _catalogue(db_session)
    claim = _new_document_claim(db_session, catalogue.id)
    key = _issue_key(db_session)

    response = client.post(
        EMIT_URL.format(catalogue_id=catalogue.id),
        headers={"X-API-Key": key},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["skipped_count"] == 0
    assert body["created_count"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["claim_id"] == str(claim.id)
    assert body["items"][0]["skip_reason"] is None
    suggestion_id = uuid.UUID(body["items"][0]["suggestion_id"])
    row = db_session.get(Suggestion, suggestion_id)
    assert row is not None
    assert row.status == SuggestionStatus.PENDING
    assert row.kind == SuggestionKind.NEW_DOCUMENT
    assert row.source_type == SuggestionSource.CRAWLER


def test_emit_skips_requirement_claim_without_resolved_document_uuids(
    client: TestClient[Litestar], db_session: Session
) -> None:
    catalogue = _catalogue(db_session)
    entity = DiscoveryEntity(
        catalogue_service_id=catalogue.id,
        canonical_url="https://example.gov/req",
    )
    db_session.add(entity)
    db_session.flush()
    db_session.add(
        DiscoveryClaim(
            discovery_entity_id=entity.id,
            kind=DiscoveryClaimKind.NEW_REQUIREMENT,
            payload={"notes_i18n": {"de": "Braucht Pass"}},
            payload_fingerprint="emit-test-req-fp",
        )
    )
    db_session.flush()
    key = _issue_key(db_session)

    response = client.post(
        EMIT_URL.format(catalogue_id=catalogue.id),
        headers={"X-API-Key": key},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["skipped_count"] == 1
    assert body["created_count"] == 0
    assert body["items"][0]["suggestion_id"] is None
    assert body["items"][0]["skip_reason"] == "unresolved_requirement_documents"
    assert db_session.query(Suggestion).count() == 0


def test_emit_replays_same_suggestion_for_duplicate_idempotency_key(
    client: TestClient[Litestar], db_session: Session
) -> None:
    catalogue = _catalogue(db_session)
    _new_document_claim(db_session, catalogue.id)
    key = _issue_key(db_session)
    url = EMIT_URL.format(catalogue_id=catalogue.id)
    headers = {"X-API-Key": key}

    first = client.post(url, headers=headers)
    second = client.post(url, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["items"][0]["suggestion_id"] == first.json()["items"][0]["suggestion_id"]
    assert second.json()["items"][0]["replayed"] is True
    assert second.json()["replayed_count"] == 1
    assert db_session.query(Suggestion).count() == 1


def test_emit_returns_401_without_api_key(client: TestClient[Litestar], db_session: Session) -> None:
    catalogue = _catalogue(db_session)

    response = client.post(EMIT_URL.format(catalogue_id=catalogue.id))

    assert response.status_code == 401


def test_emit_records_emit_attempted_discovery_event(client: TestClient[Litestar], db_session: Session) -> None:
    catalogue = _catalogue(db_session)
    _new_document_claim(db_session, catalogue.id)
    key = _issue_key(db_session)

    response = client.post(
        EMIT_URL.format(catalogue_id=catalogue.id),
        headers={"X-API-Key": key},
    )
    assert response.status_code == 200

    events = list(
        db_session.scalars(
            select(DiscoveryEvent).where(
                DiscoveryEvent.catalogue_service_id == catalogue.id,
                DiscoveryEvent.event_type == DiscoveryEventType.EMIT_ATTEMPTED,
            )
        )
    )
    assert len(events) == 1
    assert events[0].payload.get("created_count") == 1
