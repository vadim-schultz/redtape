"""Threading suggestion-time tag confidence onto a promoted document (situation-tag-hierarchy chapter 1 part B)."""

from __future__ import annotations

import uuid

import pytest
from app.features.documents.repository import DocumentRepository
from app.features.documents.service import DocumentFilters, DocumentService
from app.features.taxonomy.repository import TaxonomyRepository
from app.features.taxonomy.service import TaxonomyService
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.taxonomy import document_life_situation
from app.schema.suggestion.payload import NewDocumentPayload
from scripts.seed_taxonomy import seed_taxonomy
from sqlalchemy import select
from sqlalchemy.orm import Session


@pytest.fixture
def jurisdiction(db_session: Session) -> Jurisdiction:
    row = Jurisdiction(kind=JurisdictionKind.COUNTRY, name_i18n={"en": "Testland"}, code=f"T{uuid.uuid4().hex[:8]}")
    db_session.add(row)
    db_session.flush()
    return row


@pytest.fixture
def document_service(db_session: Session) -> DocumentService:
    seed_taxonomy(db_session)
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


def test_create_from_suggestion_persists_the_given_situation_leaf_codes(
    document_service: DocumentService, db_session: Session, jurisdiction: Jurisdiction
) -> None:
    payload = _payload(
        situation_codes=["moving-house"],
        situation_leaf_codes={"moving-house": "1050200"},
    )

    document = document_service.create_from_suggestion(payload, jurisdiction.id, "residency-permit")

    row = db_session.execute(
        select(document_life_situation.c.pvog_leaf_code).where(document_life_situation.c.document_id == document.id)
    ).scalar_one()
    assert row == "1050200"


def test_create_from_suggestion_without_situation_leaf_codes_leaves_the_column_null(
    document_service: DocumentService, db_session: Session, jurisdiction: Jurisdiction
) -> None:
    payload = _payload(situation_codes=["moving-house"])

    document = document_service.create_from_suggestion(payload, jurisdiction.id, "residency-permit")

    row = db_session.execute(
        select(document_life_situation.c.pvog_leaf_code).where(document_life_situation.c.document_id == document.id)
    ).scalar_one()
    assert row is None


def test_available_leaf_codes_is_empty_when_no_situation_is_selected(
    document_service: DocumentService, jurisdiction: Jurisdiction
) -> None:
    codes = document_service.available_leaf_codes(DocumentFilters(jurisdiction_id=jurisdiction.id))

    assert codes == []


def test_available_leaf_codes_is_empty_when_two_or_more_situations_are_selected(
    document_service: DocumentService, jurisdiction: Jurisdiction
) -> None:
    filters = DocumentFilters(jurisdiction_id=jurisdiction.id, situation_codes=["moving-house", "new-job"])

    codes = document_service.available_leaf_codes(filters)

    assert codes == []


def test_available_leaf_codes_returns_the_distinct_set_for_exactly_one_situation(
    document_service: DocumentService, db_session: Session, jurisdiction: Jurisdiction
) -> None:
    for leaf_code in ("1050200", "1050300", "1050200"):
        payload = _payload(
            situation_codes=["moving-house"],
            situation_leaf_codes={"moving-house": leaf_code},
        )
        document_service.create_from_suggestion(payload, jurisdiction.id, f"doc-{leaf_code}-{uuid.uuid4().hex[:6]}")

    filters = DocumentFilters(jurisdiction_id=jurisdiction.id, situation_codes=["moving-house"])
    codes = document_service.available_leaf_codes(filters)

    assert codes == ["1050200", "1050300"]


def test_get_document_detail_reads_back_the_persisted_confidence(
    document_service: DocumentService, jurisdiction: Jurisdiction
) -> None:
    payload = _payload(domain_codes=["housing"], tag_confidence={"housing": 0.73})
    document = document_service.create_from_suggestion(payload, jurisdiction.id, "residency-permit")

    detail = document_service.get_document_detail(document_id=document.id, locale="en", enabled_locales={"en"})

    assert detail is not None
    assert [(d.code, d.confidence) for d in detail.domains] == [("housing", pytest.approx(0.73))]
