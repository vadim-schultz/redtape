from __future__ import annotations

import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

import app.features.auth.dependencies as auth_dependencies
import app.features.auth.guard_session as guard_session_module
import jwt
import pytest
from app.config import settings
from app.features.auth.dependencies import router_dependencies
from app.features.auth.guards import require_role
from app.features.auth.jwt import JwtVerifier
from app.models import AppUser
from app.models.user import UserRole
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


@contextmanager
def _keep_open(session: Session) -> Iterator[Session]:
    """Stand in for `SessionLocal()`: hands the guard the fixture's session without closing it."""

    yield session


@get("/probe-moderator", sync_to_thread=False, guards=[require_role(UserRole.MODERATOR)])
def _probe_moderator(current_user: AppUser) -> dict[str, str]:
    return {"id": str(current_user.id)}


@get("/probe-admin", sync_to_thread=False, guards=[require_role(UserRole.ADMIN)])
def _probe_admin(current_user: AppUser) -> dict[str, str]:
    return {"id": str(current_user.id)}


@pytest.fixture
def client(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient[Litestar]]:
    monkeypatch.setattr(settings, "supabase_jwks_url", "https://example.supabase.co/auth/v1/.well-known/jwks.json")
    monkeypatch.setattr(settings, "supabase_jwt_issuer", ISSUER)
    verifier = JwtVerifier(key_resolver=lambda token: PUBLIC_KEY, issuer=ISSUER, audience=AUDIENCE)
    monkeypatch.setattr(auth_dependencies, "_jwt_verifier", verifier)
    monkeypatch.setattr(guard_session_module, "SessionLocal", lambda: _keep_open(db_session))
    app = Litestar(
        route_handlers=[_probe_moderator, _probe_admin],
        dependencies={
            **router_dependencies,
            "session": Provide(lambda: db_session, sync_to_thread=False),
            "jwt_verifier": Provide(lambda: verifier, sync_to_thread=False),
        },
    )
    with TestClient(app) as test_client:
        yield test_client


def _seeded_user(db_session: Session, role: UserRole) -> uuid.UUID:
    user_id = uuid.uuid4()
    db_session.add(AppUser(id=user_id, email=f"{role.value}@example.com", role=role))
    db_session.flush()
    return user_id


def test_user_role_is_forbidden_on_a_moderator_route(client: TestClient[Litestar], db_session: Session) -> None:
    sub = _seeded_user(db_session, UserRole.USER)
    token = _token(_claims(sub=str(sub), email="user@example.com"))

    response = client.get("/probe-moderator", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient role"


def test_moderator_passes_a_moderator_route(client: TestClient[Litestar], db_session: Session) -> None:
    sub = _seeded_user(db_session, UserRole.MODERATOR)
    token = _token(_claims(sub=str(sub), email="moderator@example.com"))

    response = client.get("/probe-moderator", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200


def test_admin_passes_a_moderator_route(client: TestClient[Litestar], db_session: Session) -> None:
    sub = _seeded_user(db_session, UserRole.ADMIN)
    token = _token(_claims(sub=str(sub), email="admin@example.com"))

    response = client.get("/probe-moderator", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200


def test_moderator_is_forbidden_on_an_admin_route(client: TestClient[Litestar], db_session: Session) -> None:
    sub = _seeded_user(db_session, UserRole.MODERATOR)
    token = _token(_claims(sub=str(sub), email="moderator@example.com"))

    response = client.get("/probe-admin", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403


def test_anonymous_gets_401_not_403(client: TestClient[Litestar]) -> None:
    response = client.get("/probe-moderator")

    assert response.status_code == 401
