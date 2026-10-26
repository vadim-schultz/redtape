"""HTTP behavior of discovery admin read routes (chapter 2)."""

from __future__ import annotations

import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import app.features.auth.dependencies as auth_dependencies
import app.features.auth.guard_session as guard_session_module
import jwt
import pytest
from app.config import settings
from app.features.auth.jwt import JwtVerifier
from app.main import create_app
from app.models.discovery import (
    CatalogueService,
    DiscoverySource,
    DiscoveryTask,
    DiscoveryTaskKind,
    DiscoveryTaskStatus,
)
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy.orm import Session

TASKS_URL = "/api/v1/discovery/admin/tasks"
CATALOGUE_URL = "/api/v1/discovery/admin/catalogue"
ISSUER = "https://example.supabase.co/auth/v1"
AUDIENCE = "authenticated"
ADMIN_EMAIL = "discovery-admin@example.com"


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


def _token(*, sub: uuid.UUID, email: str) -> str:
    now = int(time.time())
    payload = {
        "sub": str(sub),
        "email": email,
        "iss": ISSUER,
        "aud": AUDIENCE,
        "iat": now,
        "exp": now + 3600,
    }
    return jwt.encode(payload, PRIVATE_KEY, algorithm="RS256")


def _jurisdiction(session: Session) -> Jurisdiction:
    country = Jurisdiction(
        kind=JurisdictionKind.COUNTRY,
        name_i18n={"en": "Testland"},
        code=f"T{uuid.uuid4().hex[:8]}",
    )
    session.add(country)
    session.flush()
    return country


def _catalogue(
    session: Session,
    *,
    source: DiscoverySource = DiscoverySource.GOVDATA,
    external_id: str = "svc-1",
) -> CatalogueService:
    jurisdiction = _jurisdiction(session)
    row = CatalogueService(
        source=source,
        external_id=external_id,
        jurisdiction_id=jurisdiction.id,
        title_i18n={"de": "Leistung"},
        raw_payload={"id": external_id},
        pipeline_stage="T0",
    )
    session.add(row)
    session.flush()
    return row


OPENED_SESSIONS: list[Session] = []
CLOSED_SESSIONS: list[Session] = []


@contextmanager
def _closing(db_session: Session) -> Iterator[Session]:
    """Mimic real SessionLocal(): a separate session on the test connection, closed on exit."""

    session = Session(bind=db_session.get_bind(), autoflush=False, join_transaction_mode="create_savepoint")
    OPENED_SESSIONS.append(session)
    try:
        yield session
    finally:
        session.close()
        CLOSED_SESSIONS.append(session)


@pytest.fixture
def client(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient[Litestar]]:
    OPENED_SESSIONS.clear()
    CLOSED_SESSIONS.clear()
    monkeypatch.setattr(settings, "supabase_jwks_url", "https://example.supabase.co/auth/v1/.well-known/jwks.json")
    monkeypatch.setattr(settings, "supabase_jwt_issuer", ISSUER)
    monkeypatch.setattr(settings, "discovery_admin_emails", ADMIN_EMAIL)
    verifier = JwtVerifier(key_resolver=lambda token: PUBLIC_KEY, issuer=ISSUER, audience=AUDIENCE)
    monkeypatch.setattr(auth_dependencies, "_jwt_verifier", verifier)
    monkeypatch.setattr(guard_session_module, "SessionLocal", lambda: _closing(db_session))
    monkeypatch.setattr("app.main.provide_session", lambda: db_session)
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_get_discovery_admin_tasks_returns_pending_tasks_for_allowlisted_admin(
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

    sub = uuid.uuid4()
    response = client.get(TASKS_URL, headers={"Authorization": f"Bearer {_token(sub=sub, email=ADMIN_EMAIL)}"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == str(task.id)
    assert body["items"][0]["status"] == "pending"


def test_get_discovery_admin_tasks_returns_403_for_authenticated_non_allowlisted_user(
    client: TestClient[Litestar],
) -> None:
    sub = uuid.uuid4()
    response = client.get(
        TASKS_URL,
        headers={"Authorization": f"Bearer {_token(sub=sub, email='stranger@example.com')}"},
    )

    assert response.status_code == 403


def test_get_discovery_admin_tasks_returns_401_without_bearer(client: TestClient[Litestar]) -> None:
    response = client.get(TASKS_URL)

    assert response.status_code == 401


def test_get_discovery_admin_tasks_returns_503_when_discovery_is_disabled(
    client: TestClient[Litestar], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "discovery_admin_emails", "")
    monkeypatch.setattr(settings, "discovery_machine_opt_in", False)

    response = client.get(TASKS_URL, headers={"Authorization": f"Bearer {_token(sub=uuid.uuid4(), email=ADMIN_EMAIL)}"})

    assert response.status_code == 503
    assert OPENED_SESSIONS == []


def test_get_discovery_admin_tasks_returns_401_when_auth_is_disabled(
    client: TestClient[Litestar], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "supabase_jwks_url", None)

    response = client.get(TASKS_URL, headers={"Authorization": f"Bearer {_token(sub=uuid.uuid4(), email=ADMIN_EMAIL)}"})

    assert response.status_code == 401
    assert OPENED_SESSIONS == []


def test_guard_closes_every_session_it_opens(client: TestClient[Litestar]) -> None:
    client.get(TASKS_URL, headers={"Authorization": f"Bearer {_token(sub=uuid.uuid4(), email=ADMIN_EMAIL)}"})
    client.get(TASKS_URL, headers={"Authorization": f"Bearer {_token(sub=uuid.uuid4(), email='x@example.com')}"})

    assert len(OPENED_SESSIONS) == 2
    assert CLOSED_SESSIONS == OPENED_SESSIONS


def test_get_discovery_admin_catalogue_lists_catalogue_services_with_source_filter(
    client: TestClient[Litestar], db_session: Session
) -> None:
    _catalogue(db_session, source=DiscoverySource.GOVDATA, external_id="gov-1")
    _catalogue(db_session, source=DiscoverySource.PVOG, external_id="pvog-1")

    sub = uuid.uuid4()
    response = client.get(
        CATALOGUE_URL,
        params={"source": "govdata"},
        headers={"Authorization": f"Bearer {_token(sub=sub, email=ADMIN_EMAIL)}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["source"] == "govdata"
    assert body["summary"]["total"] == 1


def _kind_task(
    session: Session,
    catalogue: CatalogueService,
    kind: DiscoveryTaskKind,
    **fields: object,
) -> DiscoveryTask:
    task = DiscoveryTask(
        catalogue_service_id=catalogue.id,
        kind=kind,
        target_url="https://example.gov/service",
        status=DiscoveryTaskStatus.PENDING,
        **fields,
    )
    session.add(task)
    session.flush()
    return task


ADMIN_SUB = uuid.uuid4()


def _admin_headers() -> dict[str, str]:
    """Return bearer headers for one stable admin user, so repeated calls reuse the same app_user row."""
    return {"Authorization": f"Bearer {_token(sub=ADMIN_SUB, email=ADMIN_EMAIL)}"}


def test_admin_tasks_lists_kind_attempts_and_not_before(client: TestClient[Litestar], db_session: Session) -> None:
    catalogue = _catalogue(db_session)
    retry_at = datetime.now(UTC) + timedelta(hours=2)
    _kind_task(
        db_session,
        catalogue,
        DiscoveryTaskKind.HARVEST_PAYLOAD,
        attempt_count=2,
        not_before=retry_at,
        input_key="pvog-payload@1",
    )
    _kind_task(db_session, catalogue, DiscoveryTaskKind.FETCH_URL)

    items = client.get(TASKS_URL, headers=_admin_headers()).json()["items"]

    by_kind = {item["kind"]: item for item in items}
    harvest, fetch = by_kind["harvest_payload"], by_kind["fetch_url"]
    assert (harvest["attempt_count"], harvest["input_key"]) == (2, "pvog-payload@1")
    assert datetime.fromisoformat(harvest["not_before"]) == retry_at
    assert (fetch["attempt_count"], fetch["not_before"], fetch["input_key"]) == (0, None, None)


def test_admin_tasks_filters_by_kind_and_rejects_an_invalid_kind(
    client: TestClient[Litestar], db_session: Session
) -> None:
    catalogue = _catalogue(db_session)
    _kind_task(db_session, catalogue, DiscoveryTaskKind.HARVEST_PAYLOAD)
    _kind_task(db_session, catalogue, DiscoveryTaskKind.FETCH_URL)

    filtered = client.get(TASKS_URL, params={"kind": "harvest_payload"}, headers=_admin_headers())
    invalid = client.get(TASKS_URL, params={"kind": "bogus_kind"}, headers=_admin_headers())

    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    assert [item["kind"] for item in filtered.json()["items"]] == ["harvest_payload"]
    assert invalid.status_code == 422
