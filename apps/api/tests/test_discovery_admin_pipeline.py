"""HTTP tests for discovery admin pipeline aggregate."""

from __future__ import annotations

import uuid

from app.main import Litestar
from app.models.discovery import (
    CatalogueService,
    DiscoveryEvent,
    DiscoveryEventType,
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


def test_get_catalogue_pipeline_unknown_id_writes_nothing(
    client: TestClient[Litestar], db_session: Session
) -> None:
    catalogue = _catalogue(db_session)
    response = client.get(
        PIPELINE_URL.format(catalogue_id=uuid.uuid4()),
        headers={"Authorization": f"Bearer {_token(sub=uuid.uuid4(), email=ADMIN_EMAIL)}"},
    )

    assert response.status_code == 404
    db_session.flush()
    db_session.expire_all()
    assert catalogue.pipeline_stage == "T0"
