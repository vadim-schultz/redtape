from __future__ import annotations

import time
import uuid
from collections.abc import Iterator

import app.features.auth.dependencies as auth_dependencies
import jwt
import pytest
from app.config import settings
from app.features.auth.jwt import JwtVerifier
from app.main import create_app
from app.models import AppUser
from app.models.user import UserRole
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy.orm import Session

URL = "/api/v1/me"
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


@pytest.fixture
def client(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient[Litestar]]:
    monkeypatch.setattr(settings, "supabase_jwks_url", "https://example.supabase.co/auth/v1/.well-known/jwks.json")
    monkeypatch.setattr(settings, "supabase_jwt_issuer", ISSUER)
    verifier = JwtVerifier(key_resolver=lambda token: PUBLIC_KEY, issuer=ISSUER, audience=AUDIENCE)
    monkeypatch.setattr(auth_dependencies, "_jwt_verifier", verifier)
    monkeypatch.setattr("app.main.provide_session", lambda: db_session)
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_me_returns_the_current_users_profile(client: TestClient[Litestar]) -> None:
    sub = str(uuid.uuid4())
    token = _token(_claims(sub=sub, email="ada@example.com", user_metadata={"full_name": "Ada Lovelace"}))

    response = client.get(URL, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {
        "id": sub,
        "email": "ada@example.com",
        "display_name": "Ada Lovelace",
        "role": "user",
    }


def test_me_returns_the_role_stored_in_the_database_not_the_tokens(
    client: TestClient[Litestar], db_session: Session
) -> None:
    sub = uuid.uuid4()
    db_session.add(AppUser(id=sub, email="mod@example.com", display_name="Mod", role=UserRole.MODERATOR))
    db_session.flush()
    token = _token(_claims(sub=str(sub), email="mod@example.com"))

    response = client.get(URL, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["role"] == "moderator"


def test_me_first_call_creates_the_user_row(client: TestClient[Litestar], db_session: Session) -> None:
    token = _token(_claims())
    assert db_session.query(AppUser).count() == 0

    response = client.get(URL, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert db_session.query(AppUser).count() == 1


def test_me_second_call_does_not_create_a_duplicate(client: TestClient[Litestar], db_session: Session) -> None:
    token = _token(_claims())
    client.get(URL, headers={"Authorization": f"Bearer {token}"})

    response = client.get(URL, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert db_session.query(AppUser).count() == 1


def test_me_returns_401_without_a_token(client: TestClient[Litestar]) -> None:
    response = client.get(URL)

    assert response.status_code == 401


def test_me_response_is_not_cacheable(client: TestClient[Litestar]) -> None:
    token = _token(_claims())

    response = client.get(URL, headers={"Authorization": f"Bearer {token}"})

    assert response.headers["cache-control"] == "no-store"


def test_me_response_omits_fields_outside_the_read_model(client: TestClient[Litestar]) -> None:
    token = _token(_claims())

    response = client.get(URL, headers={"Authorization": f"Bearer {token}"})

    assert set(response.json().keys()) == {"id", "email", "display_name", "role"}
