"""Double-run idempotency for discovery machine ingest (chapter 5)."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from unittest.mock import patch

import app.features.auth.guards as auth_guards
import pytest
from app.config import settings
from app.features.discovery.catalogue_upsert import CatalogueUpsertService
from app.features.discovery.repository import DiscoveryRepository
from app.main import create_app
from app.models.discovery import (
    CatalogueService,
    DiscoveryClaim,
    DiscoverySource,
    DiscoveryTask,
    DiscoveryTaskKind,
    DiscoveryTaskStatus,
)
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.schema.discovery.machine import CatalogueBatchItem
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from test_discovery_machine_api import BATCH_URL, _batch_item, _issue_key
from test_discovery_machine_entities import CLAIMS_URL, ENTITIES_URL

CLAIM_PAYLOAD = {
    "title_i18n": {"de": "Ausweis"},
    "official_url": "https://example.gov/doc",
}


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


def _post_batch_twice(
    client: TestClient[Litestar],
    db_session: Session,
    country: Jurisdiction,
    *,
    external_id: str = "idempotent-svc",
) -> tuple[uuid.UUID, uuid.UUID]:
    key = _issue_key(db_session)
    item = _batch_item(country, external_id=external_id)
    first = client.post(BATCH_URL, json={"items": [item]}, headers={"X-API-Key": key})
    second = client.post(BATCH_URL, json={"items": [item]}, headers={"X-API-Key": key})
    assert first.status_code == 201
    assert second.status_code == 201
    catalogue_id = uuid.UUID(first.json()["items"][0]["id"])
    first_task_id = uuid.UUID(first.json()["items"][0]["task_id"])
    second_task_id = uuid.UUID(second.json()["items"][0]["task_id"])
    assert first_task_id == second_task_id
    return catalogue_id, first_task_id


def test_batch_upsert_twice_single_pending_fetch_url_task_per_portal(
    client: TestClient[Litestar],
    db_session: Session,
    country: Jurisdiction,
) -> None:
    """batch upsert twice · single pending fetch_url task per portal."""
    catalogue_id, task_id = _post_batch_twice(client, db_session, country)

    pending_fetch = list(
        db_session.scalars(
            select(DiscoveryTask).where(
                DiscoveryTask.catalogue_service_id == catalogue_id,
                DiscoveryTask.kind == DiscoveryTaskKind.FETCH_URL,
                DiscoveryTask.status == DiscoveryTaskStatus.PENDING,
            )
        )
    )
    assert len(pending_fetch) == 1
    assert pending_fetch[0].id == task_id


def test_batch_upsert_twice_catalogue_count_unchanged(
    client: TestClient[Litestar],
    db_session: Session,
    country: Jurisdiction,
) -> None:
    """batch upsert twice · catalogue count unchanged."""
    _post_batch_twice(client, db_session, country, external_id="count-stable")

    total = int(db_session.scalar(select(func.count()).select_from(CatalogueService)) or 0)
    assert total == 1


def test_append_claim_twice_same_fingerprint_one_claim_row(
    client: TestClient[Litestar],
    db_session: Session,
    country: Jurisdiction,
) -> None:
    """append_claim twice same fingerprint · one claim row."""
    key = _issue_key(db_session)
    catalogue_id = uuid.UUID(
        client.post(
            BATCH_URL,
            json={"items": [_batch_item(country, external_id="claim-dedup")]},
            headers={"X-API-Key": key},
        ).json()["items"][0]["id"]
    )
    entity_id = uuid.UUID(
        client.post(
            ENTITIES_URL,
            json={"catalogue_service_id": str(catalogue_id), "canonical_url": "https://example.gov/doc"},
            headers={"X-API-Key": key},
        ).json()["id"]
    )

    body = {
        "discovery_entity_id": str(entity_id),
        "kind": "new_document",
        "payload": CLAIM_PAYLOAD,
        "confidence": 0.5,
    }
    first = client.post(CLAIMS_URL, json=body, headers={"X-API-Key": key})
    body["confidence"] = 0.9
    second = client.post(CLAIMS_URL, json=body, headers={"X-API-Key": key})
    assert first.status_code == 201
    assert second.status_code == 201
    assert uuid.UUID(first.json()["id"]) == uuid.UUID(second.json()["id"])

    claims = list(db_session.scalars(select(DiscoveryClaim).where(DiscoveryClaim.discovery_entity_id == entity_id)))
    assert len(claims) == 1
    assert float(claims[0].confidence or 0) == 0.9


def test_concurrent_catalogue_insert_integrity_error_recovers_to_update(
    db_session: Session,
    country: Jurisdiction,
) -> None:
    """concurrent catalogue insert · IntegrityError recovers to update."""
    repo = DiscoveryRepository(db_session)
    upserts = CatalogueUpsertService(repo)
    item = CatalogueBatchItem(
        source=DiscoverySource.GOVDATA,
        external_id="race-key",
        jurisdiction_id=country.id,
        title_i18n={"de": "Alt"},
        portal_url="https://example.gov/race",
        raw_payload={"v": 1},
    )
    row, created = upserts.upsert(item)
    assert created is True
    db_session.commit()

    updated_item = CatalogueBatchItem(
        source=DiscoverySource.GOVDATA,
        external_id="race-key",
        jurisdiction_id=country.id,
        title_i18n={"de": "Neu"},
        portal_url="https://example.gov/race",
        raw_payload={"v": 2},
    )

    original_get = repo.get_catalogue_by_source_external_id
    get_calls = 0

    def racing_get(*, source: DiscoverySource, external_id: str) -> CatalogueService | None:
        nonlocal get_calls
        get_calls += 1
        if get_calls == 1:
            return None
        return original_get(source=source, external_id=external_id)

    original_flush = db_session.flush

    def racing_flush(*args: object, **kwargs: object) -> None:
        if get_calls == 1:
            raise IntegrityError("insert", {}, Exception("uq_catalogue_service_source_external_id"))
        return original_flush(*args, **kwargs)

    with (
        patch.object(repo, "get_catalogue_by_source_external_id", racing_get),
        patch.object(db_session, "flush", racing_flush),
    ):
        result_row, created_again = upserts.upsert(updated_item)

    assert created_again is False
    assert result_row.id == row.id
    assert result_row.title_i18n["de"] == "Neu"
    assert result_row.raw_payload == {"v": 2}
