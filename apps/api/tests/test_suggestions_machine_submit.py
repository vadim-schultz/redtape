"""HTTP behavior of `POST /api/v1/suggestions` for API keys and idempotent retries (Chapter 6)."""

from __future__ import annotations

import time
import uuid
from collections.abc import Iterator

import app.features.auth.dependencies as auth_dependencies
import jwt
import pytest
from app.config import settings
from app.features.auth.jwt import JwtVerifier
from app.features.auth.repository import ApiKeyRepository
from app.features.auth.service import ApiKeyService
from app.features.suggestions.repository import SuggestionRepository
from app.features.suggestions.submitters import CrawlerSubmitter
from app.main import create_app
from app.models.document import Document
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.suggestion import Suggestion, SuggestionKind, SuggestionSource, SuggestionStatus
from app.url_normalization import normalize_url
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy.orm import Session

URL = "/api/v1/suggestions"
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


def _token_for(sub: uuid.UUID | None = None, **claim_overrides: object) -> str:
    return jwt.encode(_claims(sub=str(sub or uuid.uuid4()), **claim_overrides), PRIVATE_KEY, algorithm="RS256")


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


@pytest.fixture
def country(db_session: Session) -> Jurisdiction:
    jurisdiction = Jurisdiction(
        kind=JurisdictionKind.COUNTRY, name_i18n={"en": "Testland"}, code=f"T{uuid.uuid4().hex[:8]}"
    )
    db_session.add(jurisdiction)
    db_session.flush()
    return jurisdiction


def _issue_key(db_session: Session, name: str = "crawler-prod") -> str:
    service = ApiKeyService(ApiKeyRepository(db_session))
    key = service.issue(name)
    service.verify(key)
    db_session.flush()
    return key


def _revoke_key(db_session: Session, key: str) -> None:
    service = ApiKeyService(ApiKeyRepository(db_session))
    record = service.verify(key)
    service.revoke(record.key_prefix)
    db_session.flush()


def _payload(jurisdiction: Jurisdiction, **overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "kind": "new_document",
        "jurisdiction_id": str(jurisdiction.id),
        "payload": {
            "title_i18n": {"en": "Residency permit"},
            "official_url": "https://example.gov/residency",
        },
    }
    body.update(overrides)
    return body


def _document(db_session: Session, jurisdiction: Jurisdiction) -> Document:
    document = Document(jurisdiction_id=jurisdiction.id, slug="residency-permit", title_i18n={"en": "Residency permit"})
    db_session.add(document)
    db_session.flush()
    return document


def test_an_api_key_creates_a_crawler_suggestion(
    client: TestClient[Litestar], db_session: Session, country: Jurisdiction
) -> None:
    key = _issue_key(db_session)

    response = client.post(
        URL, json=_payload(country, source_url="https://example.gov/found-here"), headers={"X-API-Key": key}
    )

    assert response.status_code == 201
    assert response.json()["source_type"] == "crawler"


def test_crawler_submitter_is_shown_without_the_key_or_its_hash(
    client: TestClient[Litestar], db_session: Session, country: Jurisdiction
) -> None:
    key = _issue_key(db_session, name="crawler-prod")

    response = client.post(
        URL, json=_payload(country, source_url="https://example.gov/found-here"), headers={"X-API-Key": key}
    )

    assert response.json()["submitted_by"] == {"kind": "crawler", "display_name": "crawler-prod"}
    assert key not in response.text


def test_a_crawler_without_source_url_gets_422(
    client: TestClient[Litestar], db_session: Session, country: Jurisdiction
) -> None:
    key = _issue_key(db_session)

    response = client.post(URL, json=_payload(country), headers={"X-API-Key": key})

    assert response.status_code == 422
    assert "source_url" in response.text


def test_a_human_without_source_url_is_accepted(client: TestClient[Litestar], country: Jurisdiction) -> None:
    token = _token_for()

    response = client.post(URL, json=_payload(country), headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 201


def test_replaying_an_idempotency_key_returns_200_and_the_same_id(
    client: TestClient[Litestar], db_session: Session, country: Jurisdiction
) -> None:
    key = _issue_key(db_session)
    headers = {"X-API-Key": key, "Idempotency-Key": "retry-1"}
    body = _payload(country, source_url="https://example.gov/found-here")

    first = client.post(URL, json=body, headers=headers)
    second = client.post(URL, json=body, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert db_session.query(Suggestion).count() == 1


def test_replay_with_a_different_body_still_returns_the_original(
    client: TestClient[Litestar], db_session: Session, country: Jurisdiction
) -> None:
    key = _issue_key(db_session)
    headers = {"X-API-Key": key, "Idempotency-Key": "retry-2"}
    first_body = _payload(country, source_url="https://example.gov/found-here")

    first = client.post(URL, json=first_body, headers=headers)
    second_body = _payload(
        country,
        source_url="https://example.gov/found-here",
        payload={"title_i18n": {"en": "A different title"}, "official_url": "https://example.gov/a-different-page"},
    )
    second = client.post(URL, json=second_body, headers=headers)

    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["payload"] == first.json()["payload"]


def test_the_same_idempotency_key_from_another_api_key_creates_a_new_suggestion(
    client: TestClient[Litestar], db_session: Session, country: Jurisdiction
) -> None:
    key_one = _issue_key(db_session, name="crawler-one")
    key_two = _issue_key(db_session, name="crawler-two")
    body_one = _payload(country, source_url="https://example.gov/found-here")
    body_two = _payload(
        country,
        source_url="https://example.gov/found-here",
        payload={"title_i18n": {"en": "Other document"}, "official_url": "https://example.gov/other-document"},
    )

    first = client.post(URL, json=body_one, headers={"X-API-Key": key_one, "Idempotency-Key": "shared-key"})
    second = client.post(URL, json=body_two, headers={"X-API-Key": key_two, "Idempotency-Key": "shared-key"})

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["id"] != first.json()["id"]


def test_idempotent_replay_wins_over_the_duplicate_check(
    client: TestClient[Litestar], db_session: Session, country: Jurisdiction
) -> None:
    key = _issue_key(db_session)
    headers = {"X-API-Key": key, "Idempotency-Key": "retry-3"}
    body = _payload(country, source_url="https://example.gov/found-here")

    first = client.post(URL, json=body, headers=headers)
    second = client.post(URL, json=body, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 200
    assert db_session.query(Suggestion).count() == 1


def test_a_genuinely_different_suggestion_with_a_duplicate_url_still_gets_409(
    client: TestClient[Litestar], db_session: Session, country: Jurisdiction
) -> None:
    _document(db_session, country)
    key = _issue_key(db_session)

    response = client.post(
        URL, json=_payload(country, source_url="https://example.gov/found-here"), headers={"X-API-Key": key}
    )

    assert response.status_code == 409


def test_idempotency_key_is_ignored_for_humans(client: TestClient[Litestar], country: Jurisdiction) -> None:
    token = _token_for()
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": "human-retry"}
    body = _payload(country)

    first = client.post(URL, json=body, headers=headers)
    second = client.post(URL, json=body, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 409


def test_an_oversized_idempotency_key_gets_422(
    client: TestClient[Litestar], db_session: Session, country: Jurisdiction
) -> None:
    key = _issue_key(db_session)
    headers = {"X-API-Key": key, "Idempotency-Key": "k" * 129}

    response = client.post(URL, json=_payload(country, source_url="https://example.gov/found-here"), headers=headers)

    assert response.status_code == 422


def test_a_concurrent_retry_resolves_to_the_original(
    client: TestClient[Litestar], db_session: Session, country: Jurisdiction, monkeypatch: pytest.MonkeyPatch
) -> None:
    key = _issue_key(db_session)
    api_key = ApiKeyService(ApiKeyRepository(db_session)).verify(key)
    committed = Suggestion(
        kind=SuggestionKind.NEW_DOCUMENT,
        status=SuggestionStatus.PENDING,
        source_type=SuggestionSource.CRAWLER,
        jurisdiction_id=country.id,
        payload={"title_i18n": {"en": "Already committed"}, "official_url": "https://example.gov/already-committed"},
        source_url="https://example.gov/found-here",
        normalized_url=normalize_url("https://example.gov/already-committed"),
        submitted_by_api_key_id=api_key.id,
        idempotency_key="race-1",
    )
    db_session.add(committed)
    db_session.flush()
    db_session.commit()  # a real SAVEPOINT boundary, so the service's own rollback() below can't undo it

    seen = {"count": 0}
    real_replay = CrawlerSubmitter.find_replay

    def _blind_on_first_call(
        self: CrawlerSubmitter, repo: SuggestionRepository, idempotency_key: str | None
    ) -> Suggestion | None:
        seen["count"] += 1
        return None if seen["count"] == 1 else real_replay(self, repo, idempotency_key)

    monkeypatch.setattr(CrawlerSubmitter, "find_replay", _blind_on_first_call)

    response = client.post(
        URL,
        json=_payload(
            country,
            source_url="https://example.gov/found-here",
            payload={"title_i18n": {"en": "Brand new"}, "official_url": "https://example.gov/brand-new-page"},
        ),
        headers={"X-API-Key": key, "Idempotency-Key": "race-1"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(committed.id)
    assert db_session.query(Suggestion).count() == 1


def test_both_authorization_and_x_api_key_give_400(
    client: TestClient[Litestar], db_session: Session, country: Jurisdiction
) -> None:
    key = _issue_key(db_session)
    token = _token_for()

    response = client.post(
        URL,
        json=_payload(country, source_url="https://example.gov/found-here"),
        headers={"Authorization": f"Bearer {token}", "X-API-Key": key},
    )

    assert response.status_code == 400


def test_a_revoked_key_gets_401(client: TestClient[Litestar], db_session: Session, country: Jurisdiction) -> None:
    key = _issue_key(db_session)
    _revoke_key(db_session, key)

    response = client.post(
        URL, json=_payload(country, source_url="https://example.gov/found-here"), headers={"X-API-Key": key}
    )

    assert response.status_code == 401
