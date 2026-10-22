"""Pin discovery machine 404/422 responses before and after domain-error mapping."""

from __future__ import annotations

import uuid

from app.models.discovery import DiscoveryEntity
from app.models.jurisdiction import Jurisdiction
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from test_discovery_machine_api import BATCH_URL, _batch_item, _issue_key
from test_discovery_machine_entities import CLAIMS_URL, ENTITIES_URL, client, country  # noqa: F401

TASK_URL = "/api/v1/discovery/machine/tasks/{task_id}/{action}"
EMIT_URL = "/api/v1/discovery/machine/catalogue/{catalogue_id}/emit"
CATALOGUE_URL = "/api/v1/discovery/machine/catalogue/{catalogue_id}"


def _post(client: TestClient[Litestar], db_session: Session, url: str, body: dict[str, object] | None = None):
    headers = {"X-API-Key": _issue_key(db_session)}
    return client.post(url, json=body, headers=headers) if body is not None else client.post(url, headers=headers)


def test_unknown_catalogue_read_returns_404_with_detail(client: TestClient[Litestar], db_session: Session) -> None:
    key = _issue_key(db_session)
    response = client.get(CATALOGUE_URL.format(catalogue_id=uuid.uuid4()), headers={"X-API-Key": key})

    assert response.status_code == 404
    assert response.json() == {"status_code": 404, "detail": "Catalogue service not found"}


def test_unknown_catalogue_emit_returns_404_with_detail(client: TestClient[Litestar], db_session: Session) -> None:
    response = _post(client, db_session, EMIT_URL.format(catalogue_id=uuid.uuid4()))

    assert response.status_code == 404
    assert response.json() == {"status_code": 404, "detail": "Catalogue service not found"}


def test_unknown_task_complete_fail_and_fetch_return_404(client: TestClient[Litestar], db_session: Session) -> None:
    bodies = {"complete": None, "fail": {"error": "boom"}, "fetches": {"http_status": 200}}
    for action, body in bodies.items():
        response = _post(client, db_session, TASK_URL.format(task_id=uuid.uuid4(), action=action), body)

        assert response.status_code == 404, action
        assert response.json() == {"status_code": 404, "detail": "Discovery task not found"}


def test_entity_upsert_unknown_catalogue_returns_404(client: TestClient[Litestar], db_session: Session) -> None:
    body = {"catalogue_service_id": str(uuid.uuid4()), "canonical_url": "https://example.gov/x"}
    response = _post(client, db_session, ENTITIES_URL, body)

    assert response.status_code == 404
    assert response.json() == {"status_code": 404, "detail": "Catalogue service not found"}


def test_entity_upsert_invalid_canonical_url_returns_422(
    client: TestClient[Litestar], db_session: Session, country: Jurisdiction
) -> None:
    key = _issue_key(db_session)
    created = client.post(BATCH_URL, json={"items": [_batch_item(country)]}, headers={"X-API-Key": key})
    body = {"catalogue_service_id": created.json()["items"][0]["id"], "canonical_url": "not a url"}
    response = client.post(ENTITIES_URL, json=body, headers={"X-API-Key": key})

    assert response.status_code == 422
    assert response.json()["status_code"] == 422
    assert db_session.scalar(select(func.count()).select_from(DiscoveryEntity)) == 0


def test_claim_unknown_entity_returns_404(client: TestClient[Litestar], db_session: Session) -> None:
    body = {"discovery_entity_id": str(uuid.uuid4()), "kind": "new_document", "payload": {}}
    response = _post(client, db_session, CLAIMS_URL, body)

    assert response.status_code == 404
    assert response.json() == {"status_code": 404, "detail": "Discovery entity not found"}
