"""Machine entity and claim routes (chapter 17)."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager

import app.features.auth.guard_session as guard_session_module
import pytest
from app.config import settings
from app.main import create_app
from app.models.discovery import (
    CatalogueService,
    DiscoveryClaim,
    DiscoveryClaimKind,
    DiscoveryEntity,
    DiscoveryEvent,
    DiscoveryEventType,
)
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from test_discovery_machine_api import BATCH_URL, _batch_item, _issue_key

ENTITIES_URL = "/api/v1/discovery/machine/entities"
CLAIMS_URL = "/api/v1/discovery/machine/claims"


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


def _catalogue_id(client: TestClient[Litestar], db_session: Session, country: Jurisdiction) -> uuid.UUID:
    key = _issue_key(db_session)
    response = client.post(
        BATCH_URL,
        json={"items": [_batch_item(country, external_id="enrich-target")]},
        headers={"X-API-Key": key},
    )
    assert response.status_code == 201
    return uuid.UUID(response.json()["items"][0]["id"])


def test_post_entities_upserts_entity_under_catalogue_service(
    client: TestClient[Litestar],
    db_session: Session,
    country: Jurisdiction,
) -> None:
    """POST /entities · upserts entity under catalogue service."""
    key = _issue_key(db_session)
    catalogue_id = _catalogue_id(client, db_session, country)

    first = client.post(
        ENTITIES_URL,
        json={
            "catalogue_service_id": str(catalogue_id),
            "canonical_url": "https://fimportal.de/api/v1/leistung-steckbriefe/LB-EXAMPLE",
            "label": "Beispiel",
        },
        headers={"X-API-Key": key},
    )
    assert first.status_code == 201
    body = first.json()
    assert body["created"] is True
    entity_id = uuid.UUID(body["id"])

    second = client.post(
        ENTITIES_URL,
        json={
            "catalogue_service_id": str(catalogue_id),
            "canonical_url": "https://fimportal.de/api/v1/leistung-steckbriefe/LB-EXAMPLE",
            "label": "Aktualisiert",
        },
        headers={"X-API-Key": key},
    )
    assert second.status_code == 201
    assert second.json()["created"] is False
    assert uuid.UUID(second.json()["id"]) == entity_id

    entity = db_session.get(DiscoveryEntity, entity_id)
    assert entity is not None
    assert entity.label == "Aktualisiert"


def test_post_claims_records_new_document_claim_payload(
    client: TestClient[Litestar],
    db_session: Session,
    country: Jurisdiction,
) -> None:
    """POST /claims · records new_document claim payload."""
    key = _issue_key(db_session)
    catalogue_id = _catalogue_id(client, db_session, country)
    entity_resp = client.post(
        ENTITIES_URL,
        json={
            "catalogue_service_id": str(catalogue_id),
            "canonical_url": "https://example.gov/doc",
        },
        headers={"X-API-Key": key},
    )
    entity_id = uuid.UUID(entity_resp.json()["id"])

    claim_resp = client.post(
        CLAIMS_URL,
        json={
            "discovery_entity_id": str(entity_id),
            "kind": "new_document",
            "payload": {
                "title_i18n": {"de": "Ausweis"},
                "official_url": "https://example.gov/doc",
            },
        },
        headers={"X-API-Key": key},
    )
    assert claim_resp.status_code == 201
    claim_id = uuid.UUID(claim_resp.json()["id"])

    claim = db_session.get(DiscoveryClaim, claim_id)
    assert claim is not None
    assert claim.kind == DiscoveryClaimKind.NEW_DOCUMENT
    assert claim.payload["official_url"] == "https://example.gov/doc"

    recorded = list(
        db_session.scalars(select(DiscoveryEvent).where(DiscoveryEvent.event_type == DiscoveryEventType.CLAIM_RECORDED))
    )
    assert len(recorded) == 1


def test_post_claims_returns_422_for_invalid_payload_shape(
    client: TestClient[Litestar],
    db_session: Session,
    country: Jurisdiction,
) -> None:
    """POST /claims · returns 422 for invalid payload shape."""
    key = _issue_key(db_session)
    catalogue_id = _catalogue_id(client, db_session, country)
    entity_resp = client.post(
        ENTITIES_URL,
        json={
            "catalogue_service_id": str(catalogue_id),
            "canonical_url": "https://example.gov/bad-claim",
        },
        headers={"X-API-Key": key},
    )
    entity_id = uuid.UUID(entity_resp.json()["id"])

    response = client.post(
        CLAIMS_URL,
        json={
            "discovery_entity_id": str(entity_id),
            "kind": "new_document",
            "payload": {"title_i18n": {"de": "Ohne URL"}},
        },
        headers={"X-API-Key": key},
    )

    assert response.status_code == 422


def _post_claim(
    client: TestClient[Litestar],
    db_session: Session,
    country: Jurisdiction,
    *,
    kind: str,
    payload: dict[str, object],
) -> uuid.UUID:
    key = _issue_key(db_session)
    catalogue_id = _catalogue_id(client, db_session, country)
    entity = client.post(
        ENTITIES_URL,
        json={"catalogue_service_id": str(catalogue_id), "canonical_url": "https://example.gov/doc"},
        headers={"X-API-Key": key},
    )
    response = client.post(
        CLAIMS_URL,
        json={"discovery_entity_id": entity.json()["id"], "kind": kind, "payload": payload},
        headers={"X-API-Key": key},
    )
    assert response.status_code == 201
    return catalogue_id


def _stored_stage(db_session: Session, catalogue_id: uuid.UUID) -> str:
    db_session.flush()
    db_session.expire_all()
    row = db_session.get(CatalogueService, catalogue_id)
    assert row is not None
    return row.pipeline_stage


def test_post_claims_metadata_claim_persists_stage_t3(
    client: TestClient[Litestar], db_session: Session, country: Jurisdiction
) -> None:
    """POST /claims · unresolvable claim persists T3."""
    catalogue_id = _post_claim(client, db_session, country, kind="metadata", payload={"kurztext": "x"})

    assert _stored_stage(db_session, catalogue_id) == "T3"


def test_post_claims_resolvable_claim_persists_stage_t4(
    client: TestClient[Litestar], db_session: Session, country: Jurisdiction
) -> None:
    """POST /claims · fully resolvable claims persist T4 without any admin GET."""
    catalogue_id = _post_claim(
        client,
        db_session,
        country,
        kind="new_document",
        payload={"title_i18n": {"de": "Ausweis"}, "official_url": "https://example.gov/doc"},
    )

    assert _stored_stage(db_session, catalogue_id) == "T4"


def test_batch_upsert_persists_stage_t1_when_task_enqueued(
    client: TestClient[Litestar], db_session: Session, country: Jurisdiction
) -> None:
    """POST /catalogue/batch · enqueue advances stored stage to T1."""
    catalogue_id = _catalogue_id(client, db_session, country)

    assert _stored_stage(db_session, catalogue_id) == "T1"
