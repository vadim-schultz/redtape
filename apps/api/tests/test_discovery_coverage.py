"""HTTP behavior of discovery admin coverage metrics (chapter 19)."""

from __future__ import annotations

import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

import app.features.auth.dependencies as auth_dependencies
import app.features.discovery.guards as discovery_guards
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

COVERAGE_URL = "/api/v1/discovery/admin/coverage"
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
    external_id: str,
    pipeline_stage: str = "T0",
) -> CatalogueService:
    jurisdiction = _jurisdiction(session)
    row = CatalogueService(
        source=source,
        external_id=external_id,
        jurisdiction_id=jurisdiction.id,
        title_i18n={"de": "Leistung"},
        raw_payload={"id": external_id},
        pipeline_stage=pipeline_stage,
    )
    session.add(row)
    session.flush()
    return row


def _task(
    session: Session,
    *,
    catalogue: CatalogueService,
    status: DiscoveryTaskStatus,
) -> DiscoveryTask:
    task = DiscoveryTask(
        catalogue_service_id=catalogue.id,
        kind=DiscoveryTaskKind.FETCH_URL,
        target_url="https://example.gov/service",
        status=status,
    )
    session.add(task)
    session.flush()
    return task


@contextmanager
def _keep_open(session: Session) -> Iterator[Session]:
    yield session


@pytest.fixture
def client(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient[Litestar]]:
    monkeypatch.setattr(settings, "supabase_jwks_url", "https://example.supabase.co/auth/v1/.well-known/jwks.json")
    monkeypatch.setattr(settings, "supabase_jwt_issuer", ISSUER)
    monkeypatch.setattr(settings, "discovery_admin_emails", ADMIN_EMAIL)
    verifier = JwtVerifier(key_resolver=lambda token: PUBLIC_KEY, issuer=ISSUER, audience=AUDIENCE)
    monkeypatch.setattr(auth_dependencies, "_jwt_verifier", verifier)
    monkeypatch.setattr(discovery_guards, "SessionLocal", lambda: _keep_open(db_session))
    monkeypatch.setattr("app.main.provide_session", lambda: db_session)
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_get_discovery_admin_coverage_returns_counts_for_seeded_mixed_sources(
    client: TestClient[Litestar], db_session: Session
) -> None:
    gov_a = _catalogue(db_session, source=DiscoverySource.GOVDATA, external_id="gov-a", pipeline_stage="T0")
    _catalogue(db_session, source=DiscoverySource.GOVDATA, external_id="gov-b", pipeline_stage="T4")
    pvog = _catalogue(db_session, source=DiscoverySource.PVOG, external_id="pvog-1", pipeline_stage="T3")
    _task(db_session, catalogue=gov_a, status=DiscoveryTaskStatus.PENDING)
    _task(db_session, catalogue=pvog, status=DiscoveryTaskStatus.FAILED)

    sub = uuid.uuid4()
    response = client.get(COVERAGE_URL, headers={"Authorization": f"Bearer {_token(sub=sub, email=ADMIN_EMAIL)}"})

    assert response.status_code == 200
    body = response.json()
    assert body["by_source"] == {"govdata": 2, "pvog": 1}
    assert body["tasks_pending"] == 1
    assert body["tasks_failed"] == 1
    assert body["emit_ready_count"] == 1


def test_get_discovery_admin_coverage_returns_403_for_non_admin(client: TestClient[Litestar]) -> None:
    sub = uuid.uuid4()
    response = client.get(
        COVERAGE_URL,
        headers={"Authorization": f"Bearer {_token(sub=sub, email='stranger@example.com')}"},
    )

    assert response.status_code == 403
