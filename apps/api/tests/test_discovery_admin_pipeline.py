"""HTTP tests for discovery admin pipeline aggregate."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from app.main import Litestar
from app.models.discovery import (
    CatalogueService,
    DiscoveryClaim,
    DiscoveryClaimKind,
    DiscoveryEntity,
    DiscoveryEvent,
    DiscoveryEventType,
    DiscoveryFetchLog,
    DiscoveryTask,
    DiscoveryTaskKind,
    DiscoveryTaskStatus,
)
from litestar.testing import TestClient
from sqlalchemy.orm import Session

from test_discovery_admin_api import ADMIN_EMAIL, _catalogue, _token

PIPELINE_URL = "/api/v1/discovery/admin/catalogue/{catalogue_id}/pipeline"


def test_get_catalogue_pipeline_returns_404_for_unknown_id(
    client: TestClient[Litestar],
) -> None:
    unknown = uuid.uuid4()
    response = client.get(
        PIPELINE_URL.format(catalogue_id=unknown),
        headers={"Authorization": f"Bearer {_token(sub=uuid.uuid4(), email=ADMIN_EMAIL)}"},
    )

    assert response.status_code == 404


def test_get_catalogue_pipeline_includes_tasks_and_events_for_seeded_row(
    client: TestClient[Litestar], db_session: Session
) -> None:
    catalogue = _catalogue(db_session)
    task = DiscoveryTask(
        catalogue_service_id=catalogue.id,
        kind=DiscoveryTaskKind.FETCH_URL,
        target_url="https://example.gov/service",
        status=DiscoveryTaskStatus.PENDING,
    )
    db_session.add(task)
    db_session.flush()
    event = DiscoveryEvent(
        event_type=DiscoveryEventType.TASK_ENQUEUED,
        catalogue_service_id=catalogue.id,
        discovery_task_id=task.id,
        payload={"kind": task.kind.value},
    )
    db_session.add(event)
    db_session.flush()

    response = client.get(
        PIPELINE_URL.format(catalogue_id=catalogue.id),
        headers={"Authorization": f"Bearer {_token(sub=uuid.uuid4(), email=ADMIN_EMAIL)}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["derived_stage"] == "T1"
    assert len(body["tasks"]) == 1
    assert body["tasks"][0]["id"] == str(task.id)
    assert len(body["events"]) == 1
    assert body["events"][0]["event_type"] == "task_enqueued"


def test_get_catalogue_pipeline_is_idempotent_and_leaves_stored_stage_unchanged(
    client: TestClient[Litestar], db_session: Session
) -> None:
    catalogue = _catalogue(db_session)
    db_session.add(
        DiscoveryTask(
            catalogue_service_id=catalogue.id,
            kind=DiscoveryTaskKind.FETCH_URL,
            target_url="https://example.gov/service",
            status=DiscoveryTaskStatus.PENDING,
        )
    )
    db_session.flush()
    headers = {"Authorization": f"Bearer {_token(sub=uuid.uuid4(), email=ADMIN_EMAIL)}"}
    url = PIPELINE_URL.format(catalogue_id=catalogue.id)

    first = client.get(url, headers=headers)
    second = client.get(url, headers=headers)

    assert first.json() == second.json()
    assert first.json()["derived_stage"] == "T1"
    db_session.flush()
    db_session.expire_all()
    stored = db_session.get(CatalogueService, catalogue.id)
    assert stored is not None
    assert stored.pipeline_stage == "T0"


def test_get_catalogue_pipeline_unknown_id_writes_nothing(client: TestClient[Litestar], db_session: Session) -> None:
    catalogue = _catalogue(db_session)
    response = client.get(
        PIPELINE_URL.format(catalogue_id=uuid.uuid4()),
        headers={"Authorization": f"Bearer {_token(sub=uuid.uuid4(), email=ADMIN_EMAIL)}"},
    )

    assert response.status_code == 404
    db_session.flush()
    db_session.expire_all()
    assert catalogue.pipeline_stage == "T0"


def test_get_catalogue_pipeline_pins_the_shape_of_entities_claims_and_fetch_logs(
    client: TestClient[Litestar], db_session: Session
) -> None:
    catalogue = _catalogue(db_session)
    task = DiscoveryTask(
        catalogue_service_id=catalogue.id,
        kind=DiscoveryTaskKind.FETCH_URL,
        target_url="https://example.gov/service",
        status=DiscoveryTaskStatus.PENDING,
    )
    entity = DiscoveryEntity(catalogue_service_id=catalogue.id, canonical_url="https://example.gov/a", label="A")
    db_session.add_all([task, entity])
    db_session.flush()
    claim = DiscoveryClaim(
        discovery_entity_id=entity.id,
        kind=DiscoveryClaimKind.METADATA,
        payload={"k": "v"},
        payload_fingerprint="f" * 64,
        confidence=Decimal("0.5"),
    )
    log = DiscoveryFetchLog(discovery_task_id=task.id, http_status=200, fetched_at=datetime.now(UTC))
    db_session.add_all([claim, log])
    db_session.flush()

    response = client.get(
        PIPELINE_URL.format(catalogue_id=catalogue.id),
        headers={"Authorization": f"Bearer {_token(sub=uuid.uuid4(), email=ADMIN_EMAIL)}"},
    )

    body = response.json()
    assert set(body["entities"][0]) == {"id", "catalogue_service_id", "canonical_url", "label", "created_at"}
    assert body["claims"][0]["kind"] == "metadata"
    assert body["claims"][0]["confidence"] == 0.5
    assert body["claims"][0]["payload"] == {"k": "v"}
    assert body["fetch_logs"][0]["http_status"] == 200
    assert set(body["fetch_logs"][0]) == {
        "id",
        "discovery_task_id",
        "http_status",
        "fetched_at",
        "content_type",
        "byte_length",
        "error_message",
    }


def test_get_catalogue_pipeline_pins_keys_and_values_of_every_pipeline_list(
    client: TestClient[Litestar], db_session: Session
) -> None:
    catalogue = _catalogue(db_session)
    task = DiscoveryTask(
        catalogue_service_id=catalogue.id,
        kind=DiscoveryTaskKind.FETCH_URL,
        target_url="https://example.gov/service",
        status=DiscoveryTaskStatus.PENDING,
    )
    entity = DiscoveryEntity(catalogue_service_id=catalogue.id, canonical_url="https://example.gov/a", label="A")
    db_session.add_all([task, entity])
    db_session.flush()
    claim = DiscoveryClaim(
        discovery_entity_id=entity.id,
        kind=DiscoveryClaimKind.METADATA,
        payload={"k": "v"},
        payload_fingerprint="a" * 64,
        confidence=Decimal("0.5"),
    )
    event = DiscoveryEvent(
        event_type=DiscoveryEventType.TASK_ENQUEUED,
        catalogue_service_id=catalogue.id,
        discovery_task_id=task.id,
        payload={"kind": "fetch_url"},
    )
    db_session.add_all([claim, event, DiscoveryFetchLog(discovery_task_id=task.id, http_status=200)])
    db_session.flush()

    body = client.get(
        PIPELINE_URL.format(catalogue_id=catalogue.id),
        headers={"Authorization": f"Bearer {_token(sub=uuid.uuid4(), email=ADMIN_EMAIL)}"},
    ).json()

    assert set(body["claims"][0]) == {"id", "discovery_entity_id", "kind", "payload", "confidence", "created_at"}
    assert set(body["events"][0]) == {
        "id",
        "event_type",
        "catalogue_service_id",
        "discovery_task_id",
        "payload",
        "created_at",
    }
    assert body["events"][0]["event_type"] == "task_enqueued"
    assert body["events"][0]["payload"] == {"kind": "fetch_url"}
    assert body["events"][0]["catalogue_service_id"] == str(catalogue.id)
    assert body["claims"][0]["discovery_entity_id"] == str(entity.id)
    assert body["entities"][0]["canonical_url"] == "https://example.gov/a"
    assert body["entities"][0]["label"] == "A"
    # One typed timestamp spelling across the API ("Z", not "+00:00"): the operator-approved B3 wire change.
    assert body["entities"][0]["created_at"].endswith("Z")
    assert body["claims"][0]["created_at"].endswith("Z")
    assert body["events"][0]["created_at"].endswith("Z")
    assert body["fetch_logs"][0]["fetched_at"].endswith("Z")


def test_get_catalogue_pipeline_for_catalogue_without_rows_returns_empty_lists(
    client: TestClient[Litestar], db_session: Session
) -> None:
    catalogue = _catalogue(db_session)

    body = client.get(
        PIPELINE_URL.format(catalogue_id=catalogue.id),
        headers={"Authorization": f"Bearer {_token(sub=uuid.uuid4(), email=ADMIN_EMAIL)}"},
    ).json()

    assert body["entities"] == []
    assert body["fetch_logs"] == []
    assert body["claims"] == []
    assert body["events"] == []
