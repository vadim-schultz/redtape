from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from app.features.auth.dependencies import router_dependencies
from app.features.auth.repository import ApiKeyRepository
from app.features.auth.service import ApiKeyService
from litestar import Litestar, get
from litestar.di import Provide
from litestar.testing import TestClient
from sqlalchemy.orm import Session


@get("/probe-principal", sync_to_thread=False)
def _probe_principal(principal: object) -> dict[str, str]:
    return {"kind": principal.kind, "id": principal.id}


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient[Litestar]]:
    app = Litestar(
        route_handlers=[_probe_principal],
        dependencies={
            **router_dependencies,
            "session": Provide(lambda: db_session, sync_to_thread=False),
        },
    )
    with TestClient(app) as test_client:
        yield test_client


def _issued_key(db_session: Session, name: str = "crawler-prod") -> tuple[str, uuid.UUID]:
    service = ApiKeyService(ApiKeyRepository(db_session))
    key = service.issue(name)
    record = service.verify(key)
    db_session.flush()
    return key, record.id


def test_valid_api_key_yields_a_machine_principal(client: TestClient[Litestar], db_session: Session) -> None:
    key, key_id = _issued_key(db_session)

    response = client.get("/probe-principal", headers={"X-API-Key": key})

    assert response.status_code == 200
    assert response.json() == {"kind": "crawler", "id": str(key_id)}


def test_revoked_key_returns_401(client: TestClient[Litestar], db_session: Session) -> None:
    service = ApiKeyService(ApiKeyRepository(db_session))
    key = service.issue("crawler-prod")
    record = service.verify(key)
    service.revoke(record.key_prefix)
    db_session.flush()

    response = client.get("/probe-principal", headers={"X-API-Key": key})

    assert response.status_code == 401
    assert response.json() == {"status_code": 401, "detail": "Not authenticated"}


def test_unknown_key_returns_401(client: TestClient[Litestar]) -> None:
    response = client.get("/probe-principal", headers={"X-API-Key": "rt_does-not-exist"})

    assert response.status_code == 401
    assert response.json() == {"status_code": 401, "detail": "Not authenticated"}
