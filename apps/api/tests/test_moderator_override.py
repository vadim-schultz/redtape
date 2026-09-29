"""HTTP behavior of the moderator override endpoints and the events trail (Chapter 9)."""

from __future__ import annotations

import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

import app.features.auth.dependencies as auth_dependencies
import app.features.auth.guards as guards_module
import jwt
import pytest
from app.config import settings
from app.features.auth.jwt import JwtVerifier
from app.features.events.repository import EventLogRepository
from app.features.events.service import EventLogService
from app.main import create_app
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.suggestion import Suggestion, SuggestionKind, SuggestionSource, SuggestionStatus
from app.models.suggestion_event import EventType
from app.models.user import AppUser, UserRole
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from litestar import Litestar
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


def _token_for(user_id: uuid.UUID) -> str:
    return jwt.encode(_claims(sub=str(user_id)), PRIVATE_KEY, algorithm="RS256")


@contextmanager
def _keep_open(session: Session) -> Iterator[Session]:
    """Stand in for `SessionLocal()`: hands the guard the fixture's session without closing it.

    `require_role` opens its own session independently of the request's DI session; without this,
    it would upsert the same `app_user` row through a second, uncommitted connection and deadlock
    against the fixture's open transaction (see test_role_guards.py for the same pattern).
    """

    yield session


@pytest.fixture
def client(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient[Litestar]]:
    monkeypatch.setattr(settings, "supabase_jwks_url", "https://example.supabase.co/auth/v1/.well-known/jwks.json")
    monkeypatch.setattr(settings, "supabase_jwt_issuer", ISSUER)
    verifier = JwtVerifier(key_resolver=lambda token: PUBLIC_KEY, issuer=ISSUER, audience=AUDIENCE)
    monkeypatch.setattr(auth_dependencies, "_jwt_verifier", verifier)
    monkeypatch.setattr("app.main.provide_session", lambda: db_session)
    monkeypatch.setattr(guards_module, "SessionLocal", lambda: _keep_open(db_session))
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def jurisdiction(db_session: Session) -> Jurisdiction:
    row = Jurisdiction(kind=JurisdictionKind.COUNTRY, name_i18n={"en": "Testland"}, code=f"T{uuid.uuid4().hex[:8]}")
    db_session.add(row)
    db_session.flush()
    return row


@pytest.fixture
def submitter(db_session: Session) -> AppUser:
    row = AppUser(id=uuid.uuid4(), email=f"{uuid.uuid4().hex}@example.com")
    db_session.add(row)
    db_session.flush()
    return row


@pytest.fixture
def moderator(db_session: Session) -> AppUser:
    row = AppUser(id=uuid.uuid4(), email=f"{uuid.uuid4().hex}@example.com", role=UserRole.MODERATOR)
    db_session.add(row)
    db_session.flush()
    return row


@pytest.fixture
def plain_user(db_session: Session) -> AppUser:
    row = AppUser(id=uuid.uuid4(), email=f"{uuid.uuid4().hex}@example.com")
    db_session.add(row)
    db_session.flush()
    return row


def _suggestion(
    session: Session,
    jurisdiction: Jurisdiction,
    submitter: AppUser,
    status: SuggestionStatus = SuggestionStatus.PENDING,
) -> Suggestion:
    row = Suggestion(
        kind=SuggestionKind.NEW_DOCUMENT,
        status=status,
        source_type=SuggestionSource.HUMAN,
        jurisdiction_id=jurisdiction.id,
        submitted_by_user_id=submitter.id,
        payload={"title_i18n": {"en": "Residency permit"}, "official_url": "https://example.gov/residency"},
    )
    session.add(row)
    session.flush()
    return row


@pytest.fixture
def pending_suggestion(db_session: Session, jurisdiction: Jurisdiction, submitter: AppUser) -> Suggestion:
    return _suggestion(db_session, jurisdiction, submitter)


def _approve_url(suggestion_id: uuid.UUID) -> str:
    return f"/api/v1/suggestions/{suggestion_id}/approve"


def _reject_url(suggestion_id: uuid.UUID) -> str:
    return f"/api/v1/suggestions/{suggestion_id}/reject"


def _events_url(suggestion_id: uuid.UUID) -> str:
    return f"/api/v1/suggestions/{suggestion_id}/events"


def test_approve_by_a_moderator_promotes_a_pending_suggestion(
    client: TestClient[Litestar], db_session: Session, pending_suggestion: Suggestion, moderator: AppUser
) -> None:
    token = _token_for(moderator.id)

    response = client.post(_approve_url(pending_suggestion.id), headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    events = EventLogService(EventLogRepository(db_session)).list_for(pending_suggestion.id)
    assert any(e.event_type == EventType.PROMOTED for e in events)


def test_reject_by_a_moderator_with_a_reason_records_it_on_the_event(
    client: TestClient[Litestar], db_session: Session, pending_suggestion: Suggestion, moderator: AppUser
) -> None:
    token = _token_for(moderator.id)

    response = client.post(
        _reject_url(pending_suggestion.id), json={"reason": "Duplicate"}, headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    events = EventLogService(EventLogRepository(db_session)).list_for(pending_suggestion.id)
    override = next(e for e in events if e.event_type == EventType.MODERATOR_OVERRIDE)
    assert override.data["reason"] == "Duplicate"


def test_approve_by_a_plain_user_returns_403(
    client: TestClient[Litestar], pending_suggestion: Suggestion, plain_user: AppUser
) -> None:
    token = _token_for(plain_user.id)

    response = client.post(_approve_url(pending_suggestion.id), headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403


def test_approve_anonymous_returns_401(client: TestClient[Litestar], pending_suggestion: Suggestion) -> None:
    response = client.post(_approve_url(pending_suggestion.id))

    assert response.status_code == 401


def test_approve_an_already_decided_suggestion_returns_409(
    client: TestClient[Litestar],
    db_session: Session,
    jurisdiction: Jurisdiction,
    submitter: AppUser,
    moderator: AppUser,
) -> None:
    suggestion = _suggestion(db_session, jurisdiction, submitter, status=SuggestionStatus.APPROVED)
    token = _token_for(moderator.id)

    response = client.post(_approve_url(suggestion.id), headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 409


def test_reject_without_a_reason_still_succeeds(
    client: TestClient[Litestar], pending_suggestion: Suggestion, moderator: AppUser
) -> None:
    token = _token_for(moderator.id)

    response = client.post(_reject_url(pending_suggestion.id), headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


def test_get_events_as_a_moderator_sees_the_full_trace(
    client: TestClient[Litestar], db_session: Session, pending_suggestion: Suggestion, moderator: AppUser
) -> None:
    events = EventLogService(EventLogRepository(db_session))
    events.record(pending_suggestion.id, EventType.SUBMITTED)
    events.record(pending_suggestion.id, EventType.VOTED, data={"value": 1})
    events.record(
        pending_suggestion.id,
        EventType.MODERATOR_OVERRIDE,
        data={"from": "pending", "to": "rejected"},
        actor_user_id=moderator.id,
    )
    token = _token_for(moderator.id)

    response = client.get(_events_url(pending_suggestion.id), headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    event_types = {item["event_type"] for item in response.json()}
    assert event_types == {"submitted", "voted", "moderator_override"}


def test_get_events_as_a_plain_user_returns_403(
    client: TestClient[Litestar], pending_suggestion: Suggestion, plain_user: AppUser
) -> None:
    token = _token_for(plain_user.id)

    response = client.get(_events_url(pending_suggestion.id), headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403


def test_get_events_never_include_emails_or_key_hashes(
    client: TestClient[Litestar], db_session: Session, pending_suggestion: Suggestion, moderator: AppUser
) -> None:
    events = EventLogService(EventLogRepository(db_session))
    events.record(pending_suggestion.id, EventType.SUBMITTED, actor_user_id=moderator.id)
    token = _token_for(moderator.id)

    response = client.get(_events_url(pending_suggestion.id), headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert moderator.email not in response.text
    assert "@" not in response.text
