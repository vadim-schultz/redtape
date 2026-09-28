"""HTTP behavior of `POST /api/v1/suggestions` for logged-in users (Chapter 5)."""

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
from app.models.document import Document
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.suggestion import Suggestion
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


@pytest.fixture
def country(db_session: Session) -> Jurisdiction:
    jurisdiction = Jurisdiction(
        kind=JurisdictionKind.COUNTRY, name_i18n={"en": "Testland"}, code=f"T{uuid.uuid4().hex[:8]}"
    )
    db_session.add(jurisdiction)
    db_session.flush()
    return jurisdiction


def _token_for(sub: uuid.UUID | None = None, **claim_overrides: object) -> str:
    return _token(_claims(sub=str(sub or uuid.uuid4()), **claim_overrides))


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


def test_creates_a_pending_suggestion_and_returns_201(client: TestClient[Litestar], country: Jurisdiction) -> None:
    token = _token_for()

    response = client.post(URL, json=_payload(country), headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["kind"] == "new_document"
    assert body["jurisdiction_id"] == str(country.id)


def test_sets_a_location_header_to_the_new_resource(client: TestClient[Litestar], country: Jurisdiction) -> None:
    token = _token_for()

    response = client.post(URL, json=_payload(country), headers={"Authorization": f"Bearer {token}"})

    assert response.headers["location"] == f"{URL}/{response.json()['id']}"


def test_records_the_authenticated_user_as_submitter(client: TestClient[Litestar], country: Jurisdiction) -> None:
    token = _token_for()

    response = client.post(URL, json=_payload(country), headers={"Authorization": f"Bearer {token}"})

    assert response.json()["submitted_by"]["kind"] == "user"


def test_response_never_contains_the_submitters_email(client: TestClient[Litestar], country: Jurisdiction) -> None:
    token = _token_for(email="secret-address@example.com")

    response = client.post(URL, json=_payload(country), headers={"Authorization": f"Bearer {token}"})

    assert "secret-address@example.com" not in response.text


def test_returns_401_without_a_token(client: TestClient[Litestar], country: Jurisdiction) -> None:
    response = client.post(URL, json=_payload(country))

    assert response.status_code == 401


def test_returns_409_with_conflicts_for_a_duplicate_document(
    client: TestClient[Litestar], db_session: Session, country: Jurisdiction
) -> None:
    document = _document(db_session, country)
    token = _token_for()

    response = client.post(URL, json=_payload(country), headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 409
    assert response.json()["extra"]["conflicts"] == [{"type": "document", "id": str(document.id)}]


def test_a_rejected_request_leaves_no_row_behind(
    client: TestClient[Litestar], db_session: Session, country: Jurisdiction
) -> None:
    _document(db_session, country)
    token = _token_for()
    headers = {"Authorization": f"Bearer {token}"}

    duplicate = client.post(URL, json=_payload(country), headers=headers)
    invalid = client.post(
        URL,
        json=_payload(country, payload={"title_i18n": {"en": "Something else"}, "official_url": "not-a-valid-url"}),
        headers=headers,
    )

    assert duplicate.status_code == 409
    assert invalid.status_code == 422
    assert db_session.query(Suggestion).count() == 0


def test_returns_422_for_an_invalid_payload(client: TestClient[Litestar], country: Jurisdiction) -> None:
    token = _token_for()
    body = _payload(country, payload={"title_i18n": {"en": "Residency permit"}, "official_url": "not-a-valid-url"})

    response = client.post(URL, json=body, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 422


def test_returns_422_for_an_unknown_municipality_code(client: TestClient[Litestar]) -> None:
    token = _token_for()
    body = {
        "kind": "new_document",
        "municipality_code": "does-not-exist",
        "payload": {"title_i18n": {"en": "Residency permit"}, "official_url": "https://example.gov/residency"},
    }

    response = client.post(URL, json=body, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 422


def test_returns_422_for_an_unknown_domain_code(client: TestClient[Litestar], country: Jurisdiction) -> None:
    token = _token_for()
    body = _payload(country)
    body["payload"]["domain_codes"] = ["not-a-real-code"]  # type: ignore[index]

    response = client.post(URL, json=body, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 422


def test_ignores_client_supplied_status_and_submitter_fields(
    client: TestClient[Litestar], country: Jurisdiction
) -> None:
    token = _token_for()
    body = _payload(country, status="approved", submitted_by={"kind": "user", "display_name": "Someone else"})

    response = client.post(URL, json=body, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 422
