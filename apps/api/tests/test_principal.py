from __future__ import annotations

import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

import app.features.auth.guards as guards_module
import jwt
import pytest
from app.config import settings
from app.features.auth.dependencies import router_dependencies
from app.features.auth.guards import require_machine
from app.features.auth.jwt import JwtVerifier
from app.features.auth.repository import ApiKeyRepository
from app.features.auth.service import ApiKeyService
from app.models import AppUser
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from litestar import Litestar, get
from litestar.di import Provide
from litestar.testing import TestClient
from sqlalchemy.orm import Session

ISSUER = "https://example.supabase.co/auth/v1"
AUDIENCE = "authenticated"


def _rsa_keypair() -> tuple[str, str]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    public_pem = (
        private_key.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )
    return private_pem, public_pem


PRIVATE_KEY, PUBLIC_KEY = _rsa_keypair()


def _claims(**overrides: object) -> dict[str, object]:
    now = int(time.time())
    payload: dict[str, object] = {
        "sub": str(uuid.uuid4()),
        "email": "ada@example.com",
        "iss": ISSUER,
        "aud": AUDIENCE,
        "iat": now,
        "exp": now + 3600,
    }
    payload.update(overrides)
    return payload


def _token(payload: dict[str, object]) -> str:
    return jwt.encode(payload, PRIVATE_KEY, algorithm="RS256")


@get("/probe-principal", sync_to_thread=False)
def _probe_principal(principal: object) -> dict[str, str]:
    return {"kind": principal.kind, "id": principal.id}


@get("/probe-current-user", sync_to_thread=False)
def _probe_current_user(current_user: AppUser) -> dict[str, str]:
    return {"id": str(current_user.id)}


@get("/probe-machine", sync_to_thread=False, guards=[require_machine])
def _probe_machine() -> dict[str, bool]:
    return {"ok": True}


@contextmanager
def _keep_open(session: Session) -> Iterator[Session]:
    """Stand in for `SessionLocal()`: hands the guard the fixture's session without closing it."""

    yield session


@pytest.fixture
def client(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient[Litestar]]:
    monkeypatch.setattr(settings, "supabase_jwks_url", "https://example.supabase.co/auth/v1/.well-known/jwks.json")
    monkeypatch.setattr(settings, "supabase_jwt_issuer", ISSUER)
    verifier = JwtVerifier(key_resolver=lambda token: PUBLIC_KEY, issuer=ISSUER, audience=AUDIENCE)
    monkeypatch.setattr(guards_module, "SessionLocal", lambda: _keep_open(db_session))
    app = Litestar(
        route_handlers=[_probe_principal, _probe_current_user, _probe_machine],
        dependencies={
            **router_dependencies,
            "session": Provide(lambda: db_session, sync_to_thread=False),
            "jwt_verifier": Provide(lambda: verifier, sync_to_thread=False),
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


def test_valid_bearer_token_yields_a_user_principal(client: TestClient[Litestar]) -> None:
    sub = str(uuid.uuid4())
    token = _token(_claims(sub=sub))

    response = client.get("/probe-principal", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {"kind": "user", "id": sub}


def test_no_credentials_returns_401(client: TestClient[Litestar]) -> None:
    response = client.get("/probe-principal")

    assert response.status_code == 401
    assert response.json() == {"status_code": 401, "detail": "Not authenticated"}


def test_both_headers_return_400(client: TestClient[Litestar], db_session: Session) -> None:
    key, _ = _issued_key(db_session)
    token = _token(_claims())

    response = client.get(
        "/probe-principal",
        headers={"Authorization": f"Bearer {token}", "X-API-Key": key},
    )

    assert response.status_code == 400


def test_api_key_works_when_supabase_auth_is_disabled(
    client: TestClient[Litestar], db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "supabase_jwks_url", None)
    monkeypatch.setattr(settings, "supabase_jwt_issuer", None)
    key, key_id = _issued_key(db_session)

    response = client.get("/probe-principal", headers={"X-API-Key": key})

    assert response.status_code == 200
    assert response.json() == {"kind": "crawler", "id": str(key_id)}


def test_current_user_rejects_an_api_key_with_401(client: TestClient[Litestar], db_session: Session) -> None:
    key, _ = _issued_key(db_session)

    response = client.get("/probe-current-user", headers={"X-API-Key": key})

    assert response.status_code == 401
    assert response.json() == {"status_code": 401, "detail": "Not authenticated"}


def test_require_machine_human_token_gets_403(client: TestClient[Litestar]) -> None:
    token = _token(_claims())

    response = client.get("/probe-machine", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403


def test_require_machine_api_key_passes(client: TestClient[Litestar], db_session: Session) -> None:
    key, _ = _issued_key(db_session)

    response = client.get("/probe-machine", headers={"X-API-Key": key})

    assert response.status_code == 200
    assert response.json() == {"ok": True}
