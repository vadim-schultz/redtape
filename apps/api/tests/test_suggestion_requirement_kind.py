"""HTTP behavior of `POST /api/v1/suggestions` for `new_requirement` suggestions (Chapter 8)."""

from __future__ import annotations

import time
import uuid
from collections.abc import Iterator

import jwt
import pytest
from app.config import settings
from app.features.auth.jwt import JwtVerifier
from app.features.suggestions.handlers import KIND_HANDLERS
from app.main import create_app
from app.models.document import Document, DocumentRequirement
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.suggestion import Suggestion, SuggestionKind, SuggestionSource, SuggestionStatus
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from auth_support import use_jwt_verifier

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
    use_jwt_verifier(monkeypatch, verifier)
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


@pytest.fixture
def other_country(db_session: Session) -> Jurisdiction:
    jurisdiction = Jurisdiction(
        kind=JurisdictionKind.COUNTRY, name_i18n={"en": "Otherland"}, code=f"O{uuid.uuid4().hex[:8]}"
    )
    db_session.add(jurisdiction)
    db_session.flush()
    return jurisdiction


def _document(db_session: Session, jurisdiction: Jurisdiction, *, slug: str) -> Document:
    document = Document(jurisdiction_id=jurisdiction.id, slug=slug, title_i18n={"en": slug})
    db_session.add(document)
    db_session.flush()
    return document


def _edge_payload(
    *, parent_id: uuid.UUID, required_id: uuid.UUID, jurisdiction: Jurisdiction, **overrides: object
) -> dict:
    body: dict[str, object] = {
        "kind": "new_requirement",
        "jurisdiction_id": str(jurisdiction.id),
        "payload": {"parent_document_id": str(parent_id), "required_document_id": str(required_id)},
    }
    body.update(overrides)
    return body


def _post(client: TestClient[Litestar], body: dict) -> object:
    return client.post(URL, json=body, headers={"Authorization": f"Bearer {_token_for()}"})


def test_creates_a_pending_requirement_suggestion(
    client: TestClient[Litestar], db_session: Session, country: Jurisdiction
) -> None:
    parent = _document(db_session, country, slug="passport-application")
    required = _document(db_session, country, slug="birth-certificate")

    response = _post(client, _edge_payload(parent_id=parent.id, required_id=required.id, jurisdiction=country))

    assert response.status_code == 201
    body = response.json()
    assert body["kind"] == "new_requirement"
    assert body["status"] == "pending"


def test_rejects_parent_equal_to_required(
    client: TestClient[Litestar], db_session: Session, country: Jurisdiction
) -> None:
    document = _document(db_session, country, slug="passport-application")

    response = _post(client, _edge_payload(parent_id=document.id, required_id=document.id, jurisdiction=country))

    assert response.status_code == 422


def test_rejects_an_unknown_parent_document(
    client: TestClient[Litestar], db_session: Session, country: Jurisdiction
) -> None:
    required = _document(db_session, country, slug="birth-certificate")

    response = _post(client, _edge_payload(parent_id=uuid.uuid4(), required_id=required.id, jurisdiction=country))

    assert response.status_code == 422


def test_rejects_an_unknown_required_document(
    client: TestClient[Litestar], db_session: Session, country: Jurisdiction
) -> None:
    parent = _document(db_session, country, slug="passport-application")

    response = _post(client, _edge_payload(parent_id=parent.id, required_id=uuid.uuid4(), jurisdiction=country))

    assert response.status_code == 422


def test_rejects_documents_from_different_jurisdictions(
    client: TestClient[Litestar], db_session: Session, country: Jurisdiction, other_country: Jurisdiction
) -> None:
    parent = _document(db_session, country, slug="passport-application")
    required = _document(db_session, other_country, slug="birth-certificate")

    response = _post(client, _edge_payload(parent_id=parent.id, required_id=required.id, jurisdiction=country))

    assert response.status_code == 422


def test_rejects_a_direct_cycle(client: TestClient[Litestar], db_session: Session, country: Jurisdiction) -> None:
    parent = _document(db_session, country, slug="passport-application")
    required = _document(db_session, country, slug="birth-certificate")
    db_session.add(
        DocumentRequirement(parent_document_id=required.id, required_document_id=parent.id, jurisdiction_id=country.id)
    )
    db_session.flush()

    response = _post(client, _edge_payload(parent_id=parent.id, required_id=required.id, jurisdiction=country))

    assert response.status_code == 422


def test_an_existing_requirement_conflicts(
    client: TestClient[Litestar], db_session: Session, country: Jurisdiction
) -> None:
    parent = _document(db_session, country, slug="passport-application")
    required = _document(db_session, country, slug="birth-certificate")
    edge = DocumentRequirement(
        parent_document_id=parent.id, required_document_id=required.id, jurisdiction_id=country.id
    )
    db_session.add(edge)
    db_session.flush()

    response = _post(client, _edge_payload(parent_id=parent.id, required_id=required.id, jurisdiction=country))

    assert response.status_code == 409
    assert response.json()["extra"]["conflicts"] == [{"type": "document_requirement", "id": str(edge.id)}]


def test_a_pending_identical_edge_conflicts(
    client: TestClient[Litestar], db_session: Session, country: Jurisdiction
) -> None:
    parent = _document(db_session, country, slug="passport-application")
    required = _document(db_session, country, slug="birth-certificate")
    pending = Suggestion(
        kind=SuggestionKind.NEW_REQUIREMENT,
        status=SuggestionStatus.PENDING,
        source_type=SuggestionSource.HUMAN,
        jurisdiction_id=country.id,
        payload={"parent_document_id": str(parent.id), "required_document_id": str(required.id)},
    )
    db_session.add(pending)
    db_session.flush()

    response = _post(client, _edge_payload(parent_id=parent.id, required_id=required.id, jurisdiction=country))

    assert response.status_code == 409
    assert response.json()["extra"]["conflicts"] == [{"type": "suggestion", "id": str(pending.id)}]


def test_an_approved_earlier_edge_suggestion_does_not_block(
    client: TestClient[Litestar], db_session: Session, country: Jurisdiction
) -> None:
    parent = _document(db_session, country, slug="passport-application")
    required = _document(db_session, country, slug="birth-certificate")
    approved = Suggestion(
        kind=SuggestionKind.NEW_REQUIREMENT,
        status=SuggestionStatus.APPROVED,
        source_type=SuggestionSource.HUMAN,
        jurisdiction_id=country.id,
        payload={"parent_document_id": str(parent.id), "required_document_id": str(required.id)},
    )
    db_session.add(approved)
    db_session.flush()

    response = _post(client, _edge_payload(parent_id=parent.id, required_id=required.id, jurisdiction=country))

    assert response.status_code == 201


def test_two_identical_pending_edges_are_rejected_by_the_database(db_session: Session, country: Jurisdiction) -> None:
    parent = _document(db_session, country, slug="passport-application")
    required = _document(db_session, country, slug="birth-certificate")
    payload = {"parent_document_id": str(parent.id), "required_document_id": str(required.id)}
    db_session.add(
        Suggestion(
            kind=SuggestionKind.NEW_REQUIREMENT,
            status=SuggestionStatus.PENDING,
            source_type=SuggestionSource.HUMAN,
            jurisdiction_id=country.id,
            payload=payload,
        )
    )
    db_session.flush()
    db_session.add(
        Suggestion(
            kind=SuggestionKind.NEW_REQUIREMENT,
            status=SuggestionStatus.PENDING,
            source_type=SuggestionSource.HUMAN,
            jurisdiction_id=country.id,
            payload=payload,
        )
    )

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_a_payload_of_the_wrong_shape_for_its_kind_gets_422(
    client: TestClient[Litestar], db_session: Session, country: Jurisdiction
) -> None:
    body = {
        "kind": "new_requirement",
        "jurisdiction_id": str(country.id),
        "payload": {"title_i18n": {"en": "Residency permit"}, "official_url": "https://example.gov/residency"},
    }

    response = _post(client, body)

    assert response.status_code == 422


def test_kind_handlers_has_an_entry_for_every_suggestion_kind() -> None:
    assert set(KIND_HANDLERS) == set(SuggestionKind)
