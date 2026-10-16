"""Machine GET catalogue row for ingest enrich (chapter 8)."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager

import app.features.auth.guards as auth_guards
import pytest
from app.config import settings
from app.features.auth.repository import ApiKeyRepository
from app.features.auth.service import ApiKeyService
from app.main import create_app
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy.orm import Session

BATCH_URL = "/api/v1/discovery/machine/catalogue/batch"


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


def test_machine_get_catalogue_returns_raw_payload_for_seeded_row(
    client: TestClient[Litestar],
    db_session: Session,
    country: Jurisdiction,
) -> None:
    """machine GET catalogue · returns source and raw_payload for enrich."""
    api_key = _issue_key(db_session)
    batch = client.post(
        BATCH_URL,
        json={
            "items": [
                {
                    "source": "govdata",
                    "external_id": "ozg-99",
                    "jurisdiction_id": str(country.id),
                    "title_i18n": {"de": "Leistung"},
                    "raw_payload": {"fim_id": "LB-TEST"},
                }
            ]
        },
        headers={"X-API-Key": api_key},
    )
    assert batch.status_code == 201
    catalogue_id = batch.json()["items"][0]["id"]

    read = client.get(
        f"/api/v1/discovery/machine/catalogue/{catalogue_id}",
        headers={"X-API-Key": api_key},
    )
    assert read.status_code == 200
    body = read.json()
    assert body["id"] == catalogue_id
    assert body["source"] == "govdata"
    assert body["raw_payload"] == {"fim_id": "LB-TEST"}


def test_machine_get_catalogue_returns_404_for_unknown_id(
    client: TestClient[Litestar],
    db_session: Session,
) -> None:
    """machine GET catalogue · 404 when id unknown."""
    api_key = _issue_key(db_session)
    unknown = uuid.uuid4()
    read = client.get(
        f"/api/v1/discovery/machine/catalogue/{unknown}",
        headers={"X-API-Key": api_key},
    )
    assert read.status_code == 404
