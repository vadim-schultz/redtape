"""Threading suggestion-time tag confidence onto a promoted document (situation-tag-hierarchy chapter 1 part B)."""

from __future__ import annotations

import uuid

import pytest
from app.features.documents.repository import DocumentRepository
from app.features.documents.service import DocumentService
from app.features.taxonomy.repository import TaxonomyRepository
from app.features.taxonomy.service import TaxonomyService
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.schema.suggestion.payload import NewDocumentPayload
from scripts.seed_taxonomy import seed_taxonomy
from sqlalchemy.orm import Session


@pytest.fixture
def jurisdiction(db_session: Session) -> Jurisdiction:
    row = Jurisdiction(kind=JurisdictionKind.COUNTRY, name_i18n={"en": "Testland"}, code=f"T{uuid.uuid4().hex[:8]}")
    db_session.add(row)
    db_session.flush()
    return row


@pytest.fixture
def document_service(db_session: Session) -> DocumentService:
    seed_taxonomy(db_session, tags={})
    taxonomy = TaxonomyService(TaxonomyRepository(db_session))
    return DocumentService(DocumentRepository(db_session), taxonomy)


def _payload(**overrides: object) -> NewDocumentPayload:
    base: dict[str, object] = {"title_i18n": {"en": "Residency permit"}}
    base.update(overrides)
    return NewDocumentPayload.model_validate(base)


def test_create_from_suggestion_persists_the_given_tag_confidence(
    document_service: DocumentService, db_session: Session, jurisdiction: Jurisdiction
) -> None:
    payload = _payload(
        domain_codes=["housing"],
        situation_codes=["moving-house"],
        tag_confidence={"housing": 0.73, "moving-house": 0.42},
    )

    document = document_service.create_from_suggestion(payload, jurisdiction.id, "residency-permit")

    confidence = DocumentRepository(db_session).get_tag_confidence(document.id)
    assert list(confidence.domains.values()) == [pytest.approx(0.73)]
    assert list(confidence.life_situations.values()) == [pytest.approx(0.42)]


def test_create_from_suggestion_defaults_a_code_missing_from_tag_confidence_to_full_confidence(
    document_service: DocumentService, db_session: Session, jurisdiction: Jurisdiction
) -> None:
    payload = _payload(
        domain_codes=["housing", "work-employment"],
        tag_confidence={"housing": 0.5},
    )

    document = document_service.create_from_suggestion(payload, jurisdiction.id, "residency-permit")

    confidence = DocumentRepository(db_session).get_tag_confidence(document.id)
    assert sorted(confidence.domains.values()) == [pytest.approx(0.5), pytest.approx(1.0)]


def test_create_from_suggestion_without_tag_confidence_at_all_defaults_every_code_to_full_confidence(
    document_service: DocumentService, db_session: Session, jurisdiction: Jurisdiction
) -> None:
    """A `NewDocumentPayload` authored without `tag_confidence` (e.g. a hand-written admin creation) is
    treated as fully confident — the same default the link tables' own `server_default` uses.
    """
    payload = _payload(domain_codes=["housing"], situation_codes=["moving-house"])

    document = document_service.create_from_suggestion(payload, jurisdiction.id, "residency-permit")

    confidence = DocumentRepository(db_session).get_tag_confidence(document.id)
    assert list(confidence.domains.values()) == [pytest.approx(1.0)]
    assert list(confidence.life_situations.values()) == [pytest.approx(1.0)]


def test_get_document_detail_reads_back_the_persisted_confidence(
    document_service: DocumentService, jurisdiction: Jurisdiction
) -> None:
    payload = _payload(domain_codes=["housing"], tag_confidence={"housing": 0.73})
    document = document_service.create_from_suggestion(payload, jurisdiction.id, "residency-permit")

    detail = document_service.get_document_detail(document_id=document.id, locale="en", enabled_locales={"en"})

    assert detail is not None
    assert [(d.code, d.confidence) for d in detail.domains] == [("housing", pytest.approx(0.73))]
