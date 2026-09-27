from __future__ import annotations

import time
import uuid
from collections.abc import Iterator

import jwt
import pytest
from app.config import settings
from app.features.auth.dependencies import router_dependencies
from app.features.auth.jwt import JwtVerifier, TokenClaims
from app.features.auth.repository import UserRepository
from app.features.auth.service import UserService
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
OTHER_PRIVATE_KEY, _ = _rsa_keypair()


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


def _token(payload: dict[str, object], key: str = PRIVATE_KEY) -> str:
    return jwt.encode(payload, key, algorithm="RS256")


@get("/probe", sync_to_thread=False)
def _probe(current_user: AppUser) -> dict[str, str]:
    return {"id": str(current_user.id)}


@get("/probe-optional", sync_to_thread=False)
def _probe_optional(optional_user: AppUser | None) -> dict[str, str | None]:
    return {"id": str(optional_user.id) if optional_user else None}


@pytest.fixture
def client(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient[Litestar]]:
    monkeypatch.setattr(settings, "supabase_jwks_url", "https://example.supabase.co/auth/v1/.well-known/jwks.json")
    monkeypatch.setattr(settings, "supabase_jwt_issuer", ISSUER)
    verifier = JwtVerifier(key_resolver=lambda token: PUBLIC_KEY, issuer=ISSUER, audience=AUDIENCE)
    app = Litestar(
        route_handlers=[_probe, _probe_optional],
        dependencies={
            **router_dependencies,
            "session": Provide(lambda: db_session, sync_to_thread=False),
            "jwt_verifier": Provide(lambda: verifier, sync_to_thread=False),
        },
    )
    with TestClient(app) as test_client:
        yield test_client


def test_upsert_inserts_a_new_user_with_role_user(db_session: Session) -> None:
    user_id = uuid.uuid4()
    repo = UserRepository(db_session)

    user = repo.upsert(id=user_id, email="ada@example.com", display_name="Ada")
    db_session.flush()

    assert user.id == user_id
    assert user.email == "ada@example.com"
    assert user.role.value == "user"


def test_upsert_refreshes_email_and_last_seen_at_for_an_existing_user(db_session: Session) -> None:
    user_id = uuid.uuid4()
    repo = UserRepository(db_session)
    repo.upsert(id=user_id, email="old@example.com", display_name="Old Name")
    db_session.flush()
    first_seen = repo.get(user_id).last_seen_at

    updated = repo.upsert(id=user_id, email="new@example.com", display_name="New Name")
    db_session.flush()

    assert db_session.query(AppUser).count() == 1
    assert updated.id == user_id
    assert updated.email == "new@example.com"
    assert updated.display_name == "New Name"
    assert updated.last_seen_at >= first_seen


def test_resolve_lower_cases_the_email(db_session: Session) -> None:
    service = UserService(UserRepository(db_session))
    claims = TokenClaims(sub=str(uuid.uuid4()), email="Ada@Example.com", display_name="Ada")

    user = service.resolve(claims)
    db_session.flush()

    assert user.email == "ada@example.com"


def test_current_user_valid_bearer_token_returns_the_user(client: TestClient[Litestar]) -> None:
    sub = str(uuid.uuid4())
    token = _token(_claims(sub=sub))

    response = client.get("/probe", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {"id": sub}


def test_current_user_missing_header_returns_401(client: TestClient[Litestar]) -> None:
    response = client.get("/probe")

    assert response.status_code == 401
    assert response.json() == {"status_code": 401, "detail": "Not authenticated"}


def test_current_user_wrong_scheme_returns_401(client: TestClient[Litestar]) -> None:
    response = client.get("/probe", headers={"Authorization": "Basic abc"})

    assert response.status_code == 401


def test_current_user_invalid_token_returns_401_without_a_reason_in_the_body(client: TestClient[Litestar]) -> None:
    token = _token(_claims(), key=OTHER_PRIVATE_KEY)

    response = client.get("/probe", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json() == {"status_code": 401, "detail": "Not authenticated"}


def test_current_user_auth_disabled_returns_401(client: TestClient[Litestar], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "supabase_jwks_url", None)
    monkeypatch.setattr(settings, "supabase_jwt_issuer", None)
    token = _token(_claims())

    response = client.get("/probe", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_optional_user_missing_header_returns_none(client: TestClient[Litestar]) -> None:
    response = client.get("/probe-optional")

    assert response.status_code == 200
    assert response.json() == {"id": None}


def test_optional_user_invalid_token_returns_401_not_anonymous(client: TestClient[Litestar]) -> None:
    token = _token(_claims(), key=OTHER_PRIVATE_KEY)

    response = client.get("/probe-optional", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
