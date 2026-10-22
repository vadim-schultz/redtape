"""Discovery entity URL normalization and upsert deduplication."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager

import app.features.auth.guard_session as guard_session_module
import pytest
from app.config import settings
from app.features.discovery.url_normalize import normalize_canonical_url
from app.main import create_app
from app.models.discovery import DiscoveryEntity
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from test_discovery_machine_api import BATCH_URL, _batch_item, _issue_key

ENTITIES_URL = "/api/v1/discovery/machine/entities"


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
        json={"items": [_batch_item(country, external_id="dedup-target")]},
        headers={"X-API-Key": key},
    )
    assert response.status_code == 201
    return uuid.UUID(response.json()["items"][0]["id"])


def test_normalize_url_strips_trailing_slash_and_utm_params() -> None:
    """normalize_url · strips trailing slash and utm params."""
    raw = "https://Example.GOV/path/?utm_source=x&b=2#frag"
    assert normalize_canonical_url(raw) == "https://example.gov/path?b=2"


def test_entity_upsert_returns_same_id_for_equivalent_urls(
    client: TestClient[Litestar],
    db_session: Session,
    country: Jurisdiction,
) -> None:
    """entity upsert · returns same id for equivalent URLs."""
    key = _issue_key(db_session)
    catalogue_id = _catalogue_id(client, db_session, country)

    first = client.post(
        ENTITIES_URL,
        json={
            "catalogue_service_id": str(catalogue_id),
            "canonical_url": "https://example.gov/doc/",
        },
        headers={"X-API-Key": key},
    )
    assert first.status_code == 201
    first_id = uuid.UUID(first.json()["id"])

    second = client.post(
        ENTITIES_URL,
        json={
            "catalogue_service_id": str(catalogue_id),
            "canonical_url": "https://example.gov/doc?utm_campaign=test",
        },
        headers={"X-API-Key": key},
    )
    assert second.status_code == 201
    assert uuid.UUID(second.json()["id"]) == first_id
    assert second.json()["canonical_url"] == "https://example.gov/doc"


def test_entity_upsert_rejects_invalid_url(
    client: TestClient[Litestar],
    db_session: Session,
    country: Jurisdiction,
) -> None:
    """entity upsert · rejects invalid URL."""
    key = _issue_key(db_session)
    catalogue_id = _catalogue_id(client, db_session, country)

    response = client.post(
        ENTITIES_URL,
        json={
            "catalogue_service_id": str(catalogue_id),
            "canonical_url": "not-a-valid-url",
        },
        headers={"X-API-Key": key},
    )

    assert response.status_code == 422


def test_entity_upsert_keeps_distinct_paths_as_distinct_entities(
    client: TestClient[Litestar],
    db_session: Session,
    country: Jurisdiction,
) -> None:
    """entity upsert · keeps distinct paths as distinct entities."""
    key = _issue_key(db_session)
    catalogue_id = _catalogue_id(client, db_session, country)

    alpha = client.post(
        ENTITIES_URL,
        json={
            "catalogue_service_id": str(catalogue_id),
            "canonical_url": "https://example.gov/alpha",
        },
        headers={"X-API-Key": key},
    )
    beta = client.post(
        ENTITIES_URL,
        json={
            "catalogue_service_id": str(catalogue_id),
            "canonical_url": "https://example.gov/beta",
        },
        headers={"X-API-Key": key},
    )
    assert alpha.status_code == 201
    assert beta.status_code == 201
    assert uuid.UUID(alpha.json()["id"]) != uuid.UUID(beta.json()["id"])

    count = db_session.scalar(
        select(func.count()).select_from(DiscoveryEntity).where(DiscoveryEntity.catalogue_service_id == catalogue_id)
    )
    assert count == 2
