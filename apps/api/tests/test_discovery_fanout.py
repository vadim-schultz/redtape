"""Catalogue upsert fanout rules and batch integration (chapter 14)."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager

import app.features.auth.guard_session as guard_session_module
import pytest
from app.config import settings
from app.features.auth.repository import ApiKeyRepository
from app.features.auth.service import ApiKeyService
from app.features.discovery.fanout import apply_fanout_for_service, fanout_specs_for_service
from app.features.discovery.repository import DiscoveryRepository
from app.main import create_app
from app.models.discovery import (
    CatalogueService,
    DiscoveryEvent,
    DiscoveryEventType,
    DiscoverySource,
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
FIM_STECKBRIEF_KEY = "01234567890123"


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


def _govdata_service(
    db_session: Session,
    country: Jurisdiction,
    *,
    raw_payload: dict[str, object],
    external_id: str = "govdata:ozg:fanout-test",
) -> CatalogueService:
    row = CatalogueService(
        source=DiscoverySource.GOVDATA,
        external_id=external_id,
        jurisdiction_id=country.id,
        title_i18n={"de": "Leistung"},
        portal_url="https://example.gov/service",
        raw_payload=raw_payload,
        pipeline_stage="T0",
    )
    db_session.add(row)
    db_session.flush()
    return row


def _issue_key(db_session: Session) -> str:
    service = ApiKeyService(ApiKeyRepository(db_session))
    key = service.issue("discovery-ingest")
    service.verify(key)
    db_session.flush()
    return key


def _batch_item(country: Jurisdiction, **overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "source": "govdata",
        "external_id": "govdata:ozg:fanout-http",
        "jurisdiction_id": str(country.id),
        "title_i18n": {"de": "Leistung"},
        "portal_url": "https://example.gov/service",
        "raw_payload": {"ozgid": "fanout-http", "fim_id": FIM_STECKBRIEF_KEY},
    }
    body.update(overrides)
    return body


def test_fanout_enqueues_enrich_metadata_when_raw_payload_contains_fim_id(
    db_session: Session,
    country: Jurisdiction,
) -> None:
    """fanout · enqueues enrich_metadata when raw_payload contains fim_id."""
    service = _govdata_service(db_session, country, raw_payload={"fim_id": FIM_STECKBRIEF_KEY})
    repo = DiscoveryRepository(db_session)

    specs = fanout_specs_for_service(service)
    assert len(specs) == 1
    assert specs[0].kind == DiscoveryTaskKind.ENRICH_METADATA
    assert specs[0].target_url.endswith(FIM_STECKBRIEF_KEY)
    assert specs[0].priority > 100

    tasks = apply_fanout_for_service(repo, service)
    assert len(tasks) == 1
    assert tasks[0].kind == DiscoveryTaskKind.ENRICH_METADATA
    assert tasks[0].status == DiscoveryTaskStatus.PENDING

    events = list(
        db_session.scalars(
            select(DiscoveryEvent).where(
                DiscoveryEvent.catalogue_service_id == service.id,
                DiscoveryEvent.event_type == DiscoveryEventType.TASK_ENQUEUED,
            )
        )
    )
    assert len(events) == 1
    assert events[0].payload["kind"] == "enrich_metadata"


def test_fanout_does_not_duplicate_pending_enrich_task_on_re_upsert(
    db_session: Session,
    country: Jurisdiction,
) -> None:
    """fanout · does not duplicate pending enrich task on re-upsert."""
    service = _govdata_service(db_session, country, raw_payload={"fim_id": FIM_STECKBRIEF_KEY})
    repo = DiscoveryRepository(db_session)

    first = apply_fanout_for_service(repo, service)
    second = apply_fanout_for_service(repo, service)

    assert len(first) == 1
    assert second == []

    pending = list(
        db_session.scalars(
            select(DiscoveryTask).where(
                DiscoveryTask.catalogue_service_id == service.id,
                DiscoveryTask.kind == DiscoveryTaskKind.ENRICH_METADATA,
                DiscoveryTask.status == DiscoveryTaskStatus.PENDING,
            )
        )
    )
    assert len(pending) == 1


def test_fanout_skips_enrich_when_fim_id_missing(db_session: Session, country: Jurisdiction) -> None:
    """fanout · skips enrich when fim_id missing."""
    service = _govdata_service(db_session, country, raw_payload={"ozgid": "no-fim"})
    repo = DiscoveryRepository(db_session)

    assert fanout_specs_for_service(service) == []
    assert apply_fanout_for_service(repo, service) == []


def test_batch_upsert_integration_creates_fetch_and_enrich_tasks(
    client: TestClient[Litestar],
    db_session: Session,
    country: Jurisdiction,
) -> None:
    """batch upsert integration · creates fetch and enrich tasks."""
    key = _issue_key(db_session)
    response = client.post(
        BATCH_URL,
        json={"items": [_batch_item(country)]},
        headers={"X-API-Key": key},
    )

    assert response.status_code == 201
    catalogue_id = uuid.UUID(response.json()["items"][0]["id"])

    tasks = list(
        db_session.scalars(
            select(DiscoveryTask)
            .where(DiscoveryTask.catalogue_service_id == catalogue_id)
            .order_by(DiscoveryTask.priority.asc())
        )
    )
    assert len(tasks) == 2
    kinds = {task.kind for task in tasks}
    assert kinds == {DiscoveryTaskKind.FETCH_URL, DiscoveryTaskKind.ENRICH_METADATA}
    enrich = next(task for task in tasks if task.kind == DiscoveryTaskKind.ENRICH_METADATA)
    assert FIM_STECKBRIEF_KEY in enrich.target_url
    assert enrich.priority > next(task for task in tasks if task.kind == DiscoveryTaskKind.FETCH_URL).priority
