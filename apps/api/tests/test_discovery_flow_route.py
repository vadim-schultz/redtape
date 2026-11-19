"""HTTP behaviour of the pipeline flow route: admin-only, every stage with its state, spend and unused headroom."""

from __future__ import annotations

import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from typing import Any, get_args

import app.features.auth.guard_session as guard_session_module
import jwt
import pytest
from app.config import settings
from app.features.auth.jwt import JwtVerifier
from app.features.discovery.budget_resources import BudgetResource
from app.features.discovery.flow.state import StageState
from app.features.discovery.flow.topology import STAGES
from app.main import create_app
from app.models.discovery import (
    CatalogueService,
    DiscoveryRun,
    DiscoveryRunKind,
    DiscoveryRunStage,
    DiscoveryRunStatus,
    DiscoverySource,
    DiscoveryTask,
    DiscoveryTaskKind,
    DiscoveryTaskStatus,
)
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.schema.discovery.flow import FlowResource, FlowStageState
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy.orm import Session

from auth_support import use_jwt_verifier

FLOW_URL = "/api/v1/discovery/admin/flow"
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
    payload = {"sub": str(sub), "email": email, "iss": ISSUER, "aud": AUDIENCE, "iat": now, "exp": now + 3600}
    return jwt.encode(payload, PRIVATE_KEY, algorithm="RS256")


def _admin_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(sub=uuid.uuid4(), email=ADMIN_EMAIL)}"}


def _catalogue(session: Session) -> CatalogueService:
    country = Jurisdiction(kind=JurisdictionKind.COUNTRY, name_i18n={"en": "Testland"}, code=f"T{uuid.uuid4().hex[:8]}")
    session.add(country)
    session.flush()
    row = CatalogueService(
        source=DiscoverySource.GOVDATA,
        external_id=f"svc-{uuid.uuid4().hex[:8]}",
        jurisdiction_id=country.id,
        title_i18n={"de": "Leistung"},
        raw_payload={},
        pipeline_stage="T0",
    )
    session.add(row)
    session.flush()
    return row


@contextmanager
def _keep_open(session: Session) -> Iterator[Session]:
    yield session


@pytest.fixture
def client(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient[Litestar]]:
    monkeypatch.setattr(settings, "supabase_jwks_url", "https://example.supabase.co/auth/v1/.well-known/jwks.json")
    monkeypatch.setattr(settings, "supabase_jwt_issuer", ISSUER)
    monkeypatch.setattr(settings, "discovery_admin_emails", ADMIN_EMAIL)
    verifier = JwtVerifier(key_resolver=lambda token: PUBLIC_KEY, issuer=ISSUER, audience=AUDIENCE)
    use_jwt_verifier(monkeypatch, verifier)
    monkeypatch.setattr(guard_session_module, "SessionLocal", lambda: _keep_open(db_session))
    monkeypatch.setattr("app.main.provide_session", lambda: db_session)
    with TestClient(create_app()) as test_client:
        yield test_client


def _stage(body: dict[str, Any], stage_id: str) -> dict[str, Any]:
    return next(item for item in body["stages"] if item["id"] == stage_id)


def _spend_run(session: Session, *, stage: DiscoveryRunStage, started_at: datetime, spend: dict[str, float]) -> None:
    session.add(
        DiscoveryRun(
            kind=DiscoveryRunKind.WORKER_DRAIN.value,
            stage=stage.value,
            status=DiscoveryRunStatus.SUCCEEDED.value,
            started_at=started_at,
            finished_at=started_at,
            spend=spend,
        )
    )
    session.flush()


def test_the_flow_describes_every_stage_for_an_admin(client: TestClient[Litestar], db_session: Session) -> None:
    response = client.get(FLOW_URL, headers=_admin_headers())

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body["stages"]] == [stage.id for stage in STAGES]
    assert {item["state"] for item in body["stages"]} <= {state.value for state in StageState}
    assert _stage(body, "extract_page")["state"] == StageState.DEAD.value
    assert _stage(body, "embed")["last_run"] is None
    assert sorted(item["resource"] for item in body["allotments"]) == sorted(r.value for r in BudgetResource)


def test_the_flow_is_admin_only(client: TestClient[Litestar]) -> None:
    stranger = {"Authorization": f"Bearer {_token(sub=uuid.uuid4(), email='stranger@example.com')}"}

    response = client.get(FLOW_URL, headers=stranger)

    assert response.status_code == 403


def test_the_flow_answers_401_without_a_bearer(client: TestClient[Litestar]) -> None:
    assert client.get(FLOW_URL).status_code == 401


def test_edges_carry_from_to_and_manual_only(client: TestClient[Litestar]) -> None:
    body = client.get(FLOW_URL, headers=_admin_headers()).json()

    edges = {(edge["from"], edge["to"]): edge for edge in body["edges"]}
    assert edges[("render", "capture")]["manual_only"] is True
    assert edges[("seed", "render")]["manual_only"] is False
    assert all(isinstance(edge["tasks_created_24h"], int) for edge in body["edges"])


def test_spend_from_the_last_day_is_grouped_by_run_stage(client: TestClient[Litestar], db_session: Session) -> None:
    _spend_run(
        db_session,
        stage=DiscoveryRunStage.EMBED,
        started_at=datetime.now(UTC) - timedelta(hours=1),
        spend={BudgetResource.NEURONS.value: 12.5},
    )

    body = client.get(FLOW_URL, headers=_admin_headers()).json()

    neurons = next(item for item in body["allotments"] if item["resource"] == BudgetResource.NEURONS.value)
    assert neurons["spent_by_stage"] == {DiscoveryRunStage.EMBED.value: 12.5}


def test_spend_older_than_a_day_is_not_counted(client: TestClient[Litestar], db_session: Session) -> None:
    _spend_run(
        db_session,
        stage=DiscoveryRunStage.EMBED,
        started_at=datetime.now(UTC) - timedelta(hours=25),
        spend={BudgetResource.NEURONS.value: 99.0},
    )

    body = client.get(FLOW_URL, headers=_admin_headers()).json()

    neurons = next(item for item in body["allotments"] if item["resource"] == BudgetResource.NEURONS.value)
    assert neurons["spent_by_stage"] == {}


def test_a_stage_with_ready_work_and_headroom_is_unused_headroom(
    client: TestClient[Litestar], db_session: Session
) -> None:
    catalogue = _catalogue(db_session)
    db_session.add(
        DiscoveryTask(
            catalogue_service_id=catalogue.id,
            kind=DiscoveryTaskKind.RENDER_PAGE,
            target_url="https://example.gov/service",
            status=DiscoveryTaskStatus.PENDING,
        )
    )
    db_session.flush()

    body = client.get(FLOW_URL, headers=_admin_headers()).json()

    assert {"resource": BudgetResource.BROWSER_SECONDS.value, "stage": "render"} in body["unused_headroom"]
    assert all(entry["stage"] != "capture" for entry in body["unused_headroom"])
    assert _stage(body, "render")["state"] == StageState.BACKLOGGED.value
    assert _stage(body, "render")["ready"] == 1


def test_the_schema_names_match_the_state_and_resource_enums() -> None:
    """The schema copies the state and resource names, since it cannot import app.features; a drift fails here."""
    assert set(get_args(FlowStageState)) == {state.value for state in StageState}
    assert set(get_args(FlowResource)) == {resource.value for resource in BudgetResource}
