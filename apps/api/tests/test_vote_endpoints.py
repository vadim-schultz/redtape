"""HTTP behavior of PUT/DELETE `/api/v1/suggestions/{id}/vote` for logged-in users (Chapter 3)."""

from __future__ import annotations

import time
import uuid
from collections.abc import Iterator

import app.features.auth.dependencies as auth_dependencies
import jwt
import pytest
from app.config import settings
from app.features.auth.jwt import JwtVerifier
from app.features.suggestions.transitions import AlreadyDecidedError, SuggestionTransitions
from app.main import create_app
from app.models.document import Document
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.suggestion import Suggestion, SuggestionKind, SuggestionSource, SuggestionStatus
from app.models.suggestion_vote import SuggestionVote
from app.models.user import AppUser
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy import select
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


def _token_for(user_id: uuid.UUID, **claim_overrides: object) -> str:
    return _token(_claims(sub=str(user_id), **claim_overrides))


def _patch_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "supabase_jwks_url", "https://example.supabase.co/auth/v1/.well-known/jwks.json")
    monkeypatch.setattr(settings, "supabase_jwt_issuer", ISSUER)
    verifier = JwtVerifier(key_resolver=lambda token: PUBLIC_KEY, issuer=ISSUER, audience=AUDIENCE)
    monkeypatch.setattr(auth_dependencies, "_jwt_verifier", verifier)


@pytest.fixture
def client(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient[Litestar]]:
    _patch_auth(monkeypatch)
    monkeypatch.setattr("app.main.provide_session", lambda: db_session)
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def rollback_spy(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> Iterator[tuple[TestClient[Litestar], list[BaseException]]]:
    """A client whose `provide_session` rolls back on exception, like production's (`app/db.py`)."""
    _patch_auth(monkeypatch)
    rollbacks: list[BaseException] = []

    def _provide_session() -> Iterator[Session]:
        try:
            yield db_session
        except Exception as exc:
            db_session.rollback()
            rollbacks.append(exc)
            raise

    monkeypatch.setattr("app.main.provide_session", _provide_session)
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client, rollbacks


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
def voter(db_session: Session) -> AppUser:
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


def _voters(session: Session, n: int) -> list[AppUser]:
    users = [AppUser(id=uuid.uuid4(), email=f"{uuid.uuid4().hex}@example.com") for _ in range(n)]
    session.add_all(users)
    session.flush()
    return users


@pytest.fixture
def pending_suggestion(db_session: Session, jurisdiction: Jurisdiction, submitter: AppUser) -> Suggestion:
    return _suggestion(db_session, jurisdiction, submitter)


def _vote_url(suggestion_id: uuid.UUID) -> str:
    return f"/api/v1/suggestions/{suggestion_id}/vote"


def _vote_row(session: Session, suggestion_id: uuid.UUID, user_id: uuid.UUID) -> SuggestionVote | None:
    return session.scalar(
        select(SuggestionVote).where(SuggestionVote.suggestion_id == suggestion_id, SuggestionVote.user_id == user_id)
    )


def test_put_vote_records_an_up_vote_and_returns_it(
    client: TestClient[Litestar], pending_suggestion: Suggestion, voter: AppUser
) -> None:
    token = _token_for(voter.id)

    response = client.put(
        _vote_url(pending_suggestion.id), json={"value": 1}, headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "value": 1}


def test_put_vote_records_a_down_vote(
    client: TestClient[Litestar], pending_suggestion: Suggestion, voter: AppUser
) -> None:
    token = _token_for(voter.id)

    response = client.put(
        _vote_url(pending_suggestion.id), json={"value": -1}, headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "value": -1}


def test_put_vote_rejects_a_value_other_than_1_or_negative_1(
    client: TestClient[Litestar], pending_suggestion: Suggestion, voter: AppUser
) -> None:
    token = _token_for(voter.id)

    response = client.put(
        _vote_url(pending_suggestion.id), json={"value": 2}, headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 422


def test_put_vote_returns_401_without_a_token(client: TestClient[Litestar], pending_suggestion: Suggestion) -> None:
    response = client.put(_vote_url(pending_suggestion.id), json={"value": 1})

    assert response.status_code == 401


def test_put_vote_returns_403_for_the_suggestions_own_submitter(
    client: TestClient[Litestar], pending_suggestion: Suggestion, submitter: AppUser
) -> None:
    token = _token_for(submitter.id)

    response = client.put(
        _vote_url(pending_suggestion.id), json={"value": 1}, headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403


def test_put_vote_returns_409_for_a_non_pending_suggestion(
    client: TestClient[Litestar], db_session: Session, jurisdiction: Jurisdiction, submitter: AppUser, voter: AppUser
) -> None:
    suggestion = _suggestion(db_session, jurisdiction, submitter, status=SuggestionStatus.APPROVED)
    token = _token_for(voter.id)

    response = client.put(_vote_url(suggestion.id), json={"value": 1}, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 409


def test_put_vote_returns_404_for_an_unknown_suggestion(client: TestClient[Litestar], voter: AppUser) -> None:
    token = _token_for(voter.id)

    response = client.put(_vote_url(uuid.uuid4()), json={"value": 1}, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 404


def test_delete_vote_removes_an_existing_vote(
    client: TestClient[Litestar], db_session: Session, pending_suggestion: Suggestion, voter: AppUser
) -> None:
    token = _token_for(voter.id)
    client.put(_vote_url(pending_suggestion.id), json={"value": 1}, headers={"Authorization": f"Bearer {token}"})

    response = client.delete(_vote_url(pending_suggestion.id), headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 204
    assert _vote_row(db_session, pending_suggestion.id, voter.id) is None


def test_delete_vote_is_a_no_op_when_there_is_no_vote(
    client: TestClient[Litestar], pending_suggestion: Suggestion, voter: AppUser
) -> None:
    token = _token_for(voter.id)

    response = client.delete(_vote_url(pending_suggestion.id), headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 204


def test_delete_vote_returns_401_without_a_token(client: TestClient[Litestar], pending_suggestion: Suggestion) -> None:
    response = client.delete(_vote_url(pending_suggestion.id))

    assert response.status_code == 401


def test_delete_vote_returns_409_for_a_decided_suggestion_and_keeps_the_vote(
    client: TestClient[Litestar], db_session: Session, jurisdiction: Jurisdiction, submitter: AppUser, voter: AppUser
) -> None:
    suggestion = _suggestion(db_session, jurisdiction, submitter, status=SuggestionStatus.APPROVED)
    db_session.add(SuggestionVote(suggestion_id=suggestion.id, user_id=voter.id, value=1))
    db_session.flush()
    token = _token_for(voter.id)

    response = client.delete(_vote_url(suggestion.id), headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 409
    assert _vote_row(db_session, suggestion.id, voter.id) is not None


def test_delete_vote_returns_404_for_an_unknown_suggestion(client: TestClient[Litestar], voter: AppUser) -> None:
    token = _token_for(voter.id)

    response = client.delete(_vote_url(uuid.uuid4()), headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 404


def test_put_vote_returns_409_and_keeps_the_vote_when_the_promotion_is_blocked(
    rollback_spy: tuple[TestClient[Litestar], list[BaseException]],
    db_session: Session,
    jurisdiction: Jurisdiction,
    submitter: AppUser,
) -> None:
    client, rollbacks = rollback_spy
    suggestion = _suggestion(db_session, jurisdiction, submitter)
    db_session.add(
        Document(jurisdiction_id=jurisdiction.id, slug="residency-permit", title_i18n={"en": "Residency permit"})
    )
    db_session.flush()
    voters = _voters(db_session, 3)
    db_session.add_all(SuggestionVote(suggestion_id=suggestion.id, user_id=v.id, value=1) for v in voters[:2])
    db_session.flush()
    token = _token_for(voters[2].id)

    response = client.put(_vote_url(suggestion.id), json={"value": 1}, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 409
    assert response.json()["extra"] == {"value": 1}
    assert rollbacks == []
    assert _vote_row(db_session, suggestion.id, voters[2].id) is not None
    assert suggestion.status == SuggestionStatus.PENDING


def test_put_vote_returns_409_when_the_suggestion_was_decided_concurrently(
    rollback_spy: tuple[TestClient[Litestar], list[BaseException]],
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
    pending_suggestion: Suggestion,
    voter: AppUser,
) -> None:
    client, rollbacks = rollback_spy
    others = _voters(db_session, 2)
    db_session.add_all(SuggestionVote(suggestion_id=pending_suggestion.id, user_id=u.id, value=1) for u in others)
    db_session.flush()

    def _raise(self: SuggestionTransitions, *args: object, **kwargs: object) -> Suggestion:
        raise AlreadyDecidedError("decided behind our back")

    monkeypatch.setattr(SuggestionTransitions, "transition_to", _raise)
    token = _token_for(voter.id)

    response = client.put(
        _vote_url(pending_suggestion.id), json={"value": 1}, headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 409
    assert len(rollbacks) == 1
    assert _vote_row(db_session, pending_suggestion.id, voter.id) is None
