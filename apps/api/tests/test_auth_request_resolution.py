"""How many times one request verifies its credential, and whether a cached identity leaks across requests (B3)."""

from __future__ import annotations

import ast
import importlib
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import app.features.auth.guard_session as guard_session_module
import pytest
from app.config import settings
from app.features.auth.jwt import JwtVerifier
from app.features.auth.repository import ApiKeyRepository
from app.features.auth.service import ApiKeyService
from app.main import create_app
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy.orm import Session

from auth_support import use_jwt_verifier
from test_discovery_admin_api import ADMIN_EMAIL, AUDIENCE, ISSUER, PUBLIC_KEY, _token

ADMIN_TASKS_URL = "/api/v1/discovery/admin/tasks"
CLAIM_URL = "/api/v1/discovery/machine/tasks/claim"
ME_URL = "/api/v1/me"


@contextmanager
def _keep_open(session: Session) -> Iterator[Session]:
    yield session


@pytest.fixture
def client(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient[Litestar]]:
    monkeypatch.setattr(settings, "supabase_jwks_url", "https://example.supabase.co/auth/v1/.well-known/jwks.json")
    monkeypatch.setattr(settings, "supabase_jwt_issuer", ISSUER)
    monkeypatch.setattr(settings, "discovery_admin_emails", ADMIN_EMAIL)
    monkeypatch.setattr(settings, "discovery_machine_opt_in", True)
    use_jwt_verifier(monkeypatch, JwtVerifier(key_resolver=lambda token: PUBLIC_KEY, issuer=ISSUER, audience=AUDIENCE))
    monkeypatch.setattr(guard_session_module, "SessionLocal", lambda: _keep_open(db_session))
    monkeypatch.setattr("app.main.provide_session", lambda: db_session)
    with TestClient(create_app()) as test_client:
        yield test_client


def _count_calls(monkeypatch: pytest.MonkeyPatch, owner: type, name: str) -> list[object]:
    """Wrap ``owner.name`` so every call is recorded; the returned list gets one entry per call."""
    calls: list[object] = []
    original: Callable[..., Any] = getattr(owner, name)

    def spy(self: object, arg: object) -> object:
        calls.append(arg)
        return original(self, arg)

    monkeypatch.setattr(owner, name, spy)
    return calls


def _issue_key(db_session: Session, name: str) -> str:
    service = ApiKeyService(ApiKeyRepository(db_session))
    key = service.issue(name)
    db_session.flush()
    return key


def _admin_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(sub=uuid.uuid4(), email=ADMIN_EMAIL)}"}


def test_machine_claim_verifies_the_api_key_once(
    client: TestClient[Litestar], db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    key = _issue_key(db_session, "discovery-ingest")
    calls = _count_calls(monkeypatch, ApiKeyService, "verify")

    response = client.post(CLAIM_URL, json={"limit": 1}, headers={"X-API-Key": key})

    assert response.status_code == 200
    assert len(calls) == 1


def test_admin_route_verifies_the_jwt_once(client: TestClient[Litestar], monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _count_calls(monkeypatch, JwtVerifier, "verify")

    response = client.get(ADMIN_TASKS_URL, headers=_admin_headers())

    assert response.status_code == 200
    assert len(calls) == 1


def test_me_endpoint_verifies_the_jwt_once(client: TestClient[Litestar], monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _count_calls(monkeypatch, JwtVerifier, "verify")

    response = client.get(ME_URL, headers=_admin_headers())

    assert response.status_code == 200
    assert len(calls) == 1


def test_cached_identity_is_not_trusted_across_requests(
    client: TestClient[Litestar], db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    first_key = _issue_key(db_session, "crawler-one")
    second_key = _issue_key(db_session, "crawler-two")
    calls = _count_calls(monkeypatch, ApiKeyService, "verify")

    assert client.post(CLAIM_URL, json={"limit": 1}, headers={"X-API-Key": first_key}).status_code == 200
    assert client.post(CLAIM_URL, json={"limit": 1}, headers={"X-API-Key": second_key}).status_code == 200
    assert len(calls) == 2

    ApiKeyService(ApiKeyRepository(db_session)).revoke(first_key.removeprefix("rt_")[:8])
    db_session.flush()
    revoked = client.post(CLAIM_URL, json={"limit": 1}, headers={"X-API-Key": first_key})

    assert revoked.status_code == 401


def test_default_jwt_verifier_is_cached_and_patchable(monkeypatch: pytest.MonkeyPatch) -> None:
    dependencies = importlib.import_module("app.features.auth.dependencies")
    monkeypatch.setattr(settings, "supabase_jwks_url", "https://example.supabase.co/auth/v1/.well-known/jwks.json")
    dependencies.default_jwt_verifier.cache_clear()
    try:
        assert dependencies.default_jwt_verifier() is dependencies.default_jwt_verifier()
        assert dependencies.provide_jwt_verifier() is dependencies.default_jwt_verifier()
    finally:
        dependencies.default_jwt_verifier.cache_clear()


def test_auth_package_has_no_global_statement() -> None:
    auth_root = Path(__file__).resolve().parent.parent / "app" / "features" / "auth"
    offenders = [
        str(path)
        for path in sorted(auth_root.rglob("*.py"))
        if any(isinstance(node, ast.Global) for node in ast.walk(ast.parse(path.read_text())))
    ]

    assert offenders == []
