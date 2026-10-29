"""HTTP behavior of discovery admin coverage metrics (chapter 19)."""

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
    DiscoveryArtifact,
    DiscoveryArtifactKind,
    DiscoveryCandidateMention,
    DiscoveryCandidateStatus,
    DiscoveryDocumentCandidate,
    DiscoveryFetchLog,
    DiscoveryMentionRole,
    DiscoveryRun,
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
    lease_expires_at: datetime | None = None,
    kind: DiscoveryTaskKind = DiscoveryTaskKind.FETCH_URL,
    result_note: str | None = None,
) -> DiscoveryTask:
    task = DiscoveryTask(
        catalogue_service_id=catalogue.id,
        kind=kind,
        target_url="https://example.gov/service",
        status=status,
        lease_expires_at=lease_expires_at,
        result_note=result_note,
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
    monkeypatch.setattr(guard_session_module, "SessionLocal", lambda: _keep_open(db_session))
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


def _get_coverage(client: TestClient[Litestar]) -> dict[str, object]:
    token = _token(sub=uuid.uuid4(), email=ADMIN_EMAIL)
    response = client.get(COVERAGE_URL, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body: dict[str, object] = response.json()
    return body


def test_coverage_returns_total_and_status_counts_for_mixed_task_history(
    client: TestClient[Litestar], db_session: Session
) -> None:
    row = _catalogue(db_session, external_id="gov-mixed")
    for status in (
        DiscoveryTaskStatus.PENDING,
        DiscoveryTaskStatus.CLAIMED,
        DiscoveryTaskStatus.COMPLETED,
        DiscoveryTaskStatus.COMPLETED,
        DiscoveryTaskStatus.FAILED,
    ):
        _task(db_session, catalogue=row, status=status)
    task = _task(db_session, catalogue=row, status=DiscoveryTaskStatus.COMPLETED)
    db_session.add(DiscoveryFetchLog(discovery_task_id=task.id, http_status=200))
    db_session.add(DiscoveryFetchLog(discovery_task_id=task.id, http_status=500))
    db_session.flush()

    body = _get_coverage(client)

    assert body["task_counts"] == {"total": 6, "pending": 1, "claimed": 1, "completed": 3, "failed": 1}
    assert body["fetch_attempts_total"] == 2
    assert body["last_successful_run"] is None


def test_coverage_with_empty_queue_reports_zero_counts_and_no_run(client: TestClient[Litestar]) -> None:
    body = _get_coverage(client)

    assert body["task_counts"] == {"total": 0, "pending": 0, "claimed": 0, "completed": 0, "failed": 0}
    assert body["fetch_attempts_total"] == 0
    assert body["stale_claims"] == 0
    assert body["failures_by_source"] == {}
    assert body["last_successful_run"] is None


def test_coverage_reports_stale_leases_and_per_source_failures(
    client: TestClient[Litestar], db_session: Session
) -> None:
    now = datetime.now(UTC)
    gov = _catalogue(db_session, source=DiscoverySource.GOVDATA, external_id="gov-stale")
    pvog = _catalogue(db_session, source=DiscoverySource.PVOG, external_id="pvog-fail")
    _task(db_session, catalogue=gov, status=DiscoveryTaskStatus.CLAIMED, lease_expires_at=now - timedelta(minutes=1))
    _task(db_session, catalogue=gov, status=DiscoveryTaskStatus.CLAIMED, lease_expires_at=now + timedelta(minutes=10))
    _task(db_session, catalogue=gov, status=DiscoveryTaskStatus.FAILED)
    _task(db_session, catalogue=pvog, status=DiscoveryTaskStatus.FAILED)
    _task(db_session, catalogue=pvog, status=DiscoveryTaskStatus.FAILED)
    _task(db_session, catalogue=pvog, status=DiscoveryTaskStatus.COMPLETED)

    body = _get_coverage(client)

    assert body["stale_claims"] == 1
    assert body["failures_by_source"] == {"govdata": 1, "pvog": 2}


def test_coverage_returns_latest_successful_run_and_ignores_failed_and_running_runs(
    client: TestClient[Litestar], db_session: Session
) -> None:
    now = datetime.now(UTC)
    db_session.add_all(
        [
            DiscoveryRun(status="succeeded", started_at=now, finished_at=now - timedelta(hours=2), claimed_count=1),
            DiscoveryRun(status="succeeded", started_at=now, finished_at=now - timedelta(hours=1), claimed_count=7),
            DiscoveryRun(status="failed", started_at=now, finished_at=now, claimed_count=9),
            DiscoveryRun(status="running", started_at=now - timedelta(hours=3)),
        ]
    )
    db_session.flush()

    body = _get_coverage(client)

    last_run = body["last_successful_run"]
    assert isinstance(last_run, dict)
    assert last_run["claimed_count"] == 7
    assert body["stale_runs"] == 1


def _candidate(
    session: Session, catalogue: CatalogueService, key: str, status: DiscoveryCandidateStatus
) -> DiscoveryDocumentCandidate:
    row = DiscoveryDocumentCandidate(jurisdiction_id=catalogue.jurisdiction_id, key=key, status=status)
    session.add(row)
    session.flush()
    return row


def _mention(session: Session, candidate: DiscoveryDocumentCandidate, catalogue: CatalogueService, field: str) -> None:
    session.add(
        DiscoveryCandidateMention(
            candidate_id=candidate.id,
            catalogue_service_id=catalogue.id,
            role=DiscoveryMentionRole.REQUIRED,
            excerpt="Bitte mitbringen",
            source_field=field,
            extractor="pvog-payload",
            extractor_version="1",
        )
    )
    session.flush()


ZERO_COUNTS = {"total": 0, "pending": 0, "claimed": 0, "completed": 0, "failed": 0}
ALL_KINDS = {
    "fetch_url",
    "enrich_metadata",
    "harvest_payload",
    "extract_page",
    "capture_screenshot",
    "render_page",
    "llm_extract",
}


def test_coverage_returns_per_kind_status_counts_and_candidate_totals(
    client: TestClient[Litestar], db_session: Session
) -> None:
    row = _catalogue(db_session, source=DiscoverySource.PVOG, external_id="pvog-kinds")
    _task(db_session, catalogue=row, status=DiscoveryTaskStatus.PENDING)
    _task(db_session, catalogue=row, status=DiscoveryTaskStatus.COMPLETED)
    _task(db_session, catalogue=row, status=DiscoveryTaskStatus.FAILED, kind=DiscoveryTaskKind.HARVEST_PAYLOAD)
    staged = _candidate(db_session, row, "geburtsurkunde", DiscoveryCandidateStatus.STAGED)
    emitted = _candidate(db_session, row, "reisepass", DiscoveryCandidateStatus.EMITTED)
    _mention(db_session, staged, row, "details[0]")
    _mention(db_session, staged, row, "details[1]")
    _mention(db_session, emitted, row, "details[0]")

    body = _get_coverage(client)

    by_kind = body["task_counts_by_kind"]
    assert isinstance(by_kind, dict)
    assert set(by_kind) == ALL_KINDS
    assert by_kind["fetch_url"] == {"total": 2, "pending": 1, "claimed": 0, "completed": 1, "failed": 0}
    assert by_kind["harvest_payload"] == {"total": 1, "pending": 0, "claimed": 0, "completed": 0, "failed": 1}
    assert by_kind["capture_screenshot"] == ZERO_COUNTS
    assert body["task_counts"] == {"total": 3, "pending": 1, "claimed": 0, "completed": 1, "failed": 1}
    assert body["candidates"] == {"total": 2, "staged": 1, "emitted": 1, "mentions": 3}


def test_coverage_without_tasks_or_candidates_reports_every_kind_and_zero_candidates(
    client: TestClient[Litestar],
) -> None:
    body = _get_coverage(client)

    assert body["task_counts_by_kind"] == {kind: ZERO_COUNTS for kind in ALL_KINDS}
    assert body["candidates"] == {"total": 0, "staged": 0, "emitted": 0, "mentions": 0}


def _artifact(session: Session, catalogue: CatalogueService, kind: DiscoveryArtifactKind, sha: str, size: int) -> None:
    session.add(
        DiscoveryArtifact(
            catalogue_service_id=catalogue.id,
            kind=kind,
            storage_key=f"discovery/{catalogue.id}/{kind.value}/{sha}",
            sha256=sha,
            content_type="text/html",
            byte_size=size,
            source_url="https://example.gov/page",
            fetched_at=datetime.now(UTC),
        )
    )
    session.flush()


def test_coverage_reports_artifact_counts_and_bytes_per_kind(client: TestClient[Litestar], db_session: Session) -> None:
    row = _catalogue(db_session, external_id="gov-artifacts")
    _artifact(db_session, row, DiscoveryArtifactKind.HTML_SNAPSHOT, "a" * 64, 100)
    _artifact(db_session, row, DiscoveryArtifactKind.HTML_SNAPSHOT, "b" * 64, 250)
    _artifact(db_session, row, DiscoveryArtifactKind.SCREENSHOT, "c" * 64, 4000)

    artifacts = _get_coverage(client)["artifacts"]

    assert artifacts == {
        "by_kind": {"html_snapshot": {"count": 2, "bytes": 350}, "screenshot": {"count": 1, "bytes": 4000}},
        "total_bytes": 4350,
        "bytes_cap": settings.object_store_max_bytes,
    }


def test_coverage_artifacts_are_zero_when_there_are_none(client: TestClient[Litestar]) -> None:
    artifacts = _get_coverage(client)["artifacts"]

    assert artifacts == {
        "by_kind": {"html_snapshot": {"count": 0, "bytes": 0}, "screenshot": {"count": 0, "bytes": 0}},
        "total_bytes": 0,
        "bytes_cap": settings.object_store_max_bytes,
    }


NO_LLM_OUTCOMES = {"extracted": 0, "no_documents": 0, "login_wall": 0, "no_content": 0}


def _llm_task(db_session: Session, row: CatalogueService, note: str | None, kind: DiscoveryTaskKind) -> None:
    _task(db_session, catalogue=row, status=DiscoveryTaskStatus.COMPLETED, kind=kind, result_note=note)


def test_coverage_groups_llm_extract_tasks_by_result_note(client: TestClient[Litestar], db_session: Session) -> None:
    row = _catalogue(db_session, external_id="gov-llm")
    llm = DiscoveryTaskKind.LLM_EXTRACT
    for note in ("docs=7 edges=5 dropped=2", "docs=1 edges=0 dropped=0", "no_documents", "login_wall", "no_content"):
        _llm_task(db_session, row, note, llm)
    _llm_task(db_session, row, "no_content", llm)
    _llm_task(db_session, row, "login_wall", DiscoveryTaskKind.RENDER_PAGE)
    _llm_task(db_session, row, None, llm)

    body = _get_coverage(client)

    assert body["llm_outcomes"] == {"extracted": 2, "no_documents": 1, "login_wall": 1, "no_content": 2}


def test_coverage_reports_zero_llm_outcomes_when_there_are_none(client: TestClient[Litestar]) -> None:
    body = _get_coverage(client)

    assert body["llm_outcomes"] == NO_LLM_OUTCOMES


def test_coverage_with_llm_outcomes_still_requires_an_admin(client: TestClient[Litestar]) -> None:
    token = _token(sub=uuid.uuid4(), email="stranger@example.com")

    response = client.get(COVERAGE_URL, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403
    assert "llm_outcomes" not in response.text
