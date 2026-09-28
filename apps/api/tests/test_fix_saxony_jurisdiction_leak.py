from __future__ import annotations

import uuid

from app.models.document import Document, DocumentRequirement
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.locality import Locality
from app.models.suggestion import Suggestion, SuggestionKind, SuggestionSource
from scripts.fix_saxony_jurisdiction_leak import (
    FAKE_DRESDEN_ID,
    LEAKED_DISTRICT_ID,
    LEAKED_MUNICIPALITY_ID,
    repair_saxony_jurisdictions,
)
from sqlalchemy.orm import Session


def _leaked_saxony_tree(session: Session) -> None:
    country = Jurisdiction(kind=JurisdictionKind.COUNTRY, geographic_parent_id=None, code="DE")
    session.add(country)
    session.flush()
    sachsen = Jurisdiction(kind=JurisdictionKind.REGION, geographic_parent_id=country.id, code="14")
    session.add(sachsen)
    session.flush()

    leaked_district = Jurisdiction(
        id=LEAKED_DISTRICT_ID,
        kind=JurisdictionKind.REGION,
        geographic_parent_id=sachsen.id,
        code="146",
        administrative_roles=["DISTRICT"],
        name_i18n={"de": "Kreis Beispiel", "en": "Example District"},
    )
    session.add(leaked_district)
    session.flush()
    leaked_municipality = Jurisdiction(
        id=LEAKED_MUNICIPALITY_ID,
        kind=JurisdictionKind.MUNICIPALITY,
        geographic_parent_id=leaked_district.id,
        code="14612",
        name_i18n={"de": "Musterstadt", "en": "Example City"},
    )
    session.add(leaked_municipality)

    fake_dresden = Jurisdiction(
        id=FAKE_DRESDEN_ID,
        kind=JurisdictionKind.MUNICIPALITY,
        geographic_parent_id=sachsen.id,
        code="14612000",
        name_i18n={"de": "Dresden", "en": "Dresden"},
    )
    session.add(fake_dresden)
    session.flush()


def _document_referencing_fake_dresden(session: Session, slug: str) -> Document:
    doc = Document(jurisdiction_id=FAKE_DRESDEN_ID, slug=slug, title_i18n={"de": slug, "en": slug})
    session.add(doc)
    session.flush()
    return doc


def test_noop_when_fake_dresden_is_already_gone(db_session: Session) -> None:
    calls: list[None] = []

    repair_saxony_jurisdictions(db_session, reimport=lambda: calls.append(None))

    assert calls == []


def test_reimports_and_repoints_references_off_the_fake_dresden_row(db_session: Session) -> None:
    _leaked_saxony_tree(db_session)
    melde = _document_referencing_fake_dresden(db_session, "meldebescheinigung")
    ausweis = _document_referencing_fake_dresden(db_session, "personalausweis")
    requirement = DocumentRequirement(
        parent_document_id=melde.id,
        required_document_id=ausweis.id,
        jurisdiction_id=FAKE_DRESDEN_ID,
    )
    db_session.add(requirement)
    suggestion = Suggestion(
        kind=SuggestionKind.NEW_DOCUMENT,
        source_type=SuggestionSource.HUMAN,
        jurisdiction_id=FAKE_DRESDEN_ID,
        payload={"title_i18n": {"de": "x", "en": "x"}, "official_url": "https://example.com"},
    )
    db_session.add(suggestion)
    locality = Locality(municipality_id=FAKE_DRESDEN_ID, postal_code="01001", name="Altstadt")
    db_session.add(locality)
    db_session.flush()

    real_dresden_id = uuid.uuid4()

    def _fake_reimport() -> None:
        # The real import would look this up itself; the test stub only needs
        # the fake row's (already code-nulled) parent to hang the real tree off.
        sachsen_id = db_session.get(Jurisdiction, FAKE_DRESDEN_ID).geographic_parent_id
        real_district_row = Jurisdiction(
            kind=JurisdictionKind.REGION,
            geographic_parent_id=sachsen_id,
            code="real-district-14612",
            administrative_roles=["DISTRICT"],
        )
        db_session.add(real_district_row)
        db_session.flush()
        real_dresden = Jurisdiction(
            id=real_dresden_id,
            kind=JurisdictionKind.MUNICIPALITY,
            geographic_parent_id=real_district_row.id,
            code="14612000",
            name_i18n={"de": "Dresden", "en": "Dresden"},
        )
        db_session.add(real_dresden)
        db_session.commit()

    repair_saxony_jurisdictions(db_session, reimport=_fake_reimport)

    assert db_session.get(Jurisdiction, FAKE_DRESDEN_ID) is None
    assert db_session.get(Jurisdiction, LEAKED_MUNICIPALITY_ID) is None
    assert db_session.get(Jurisdiction, LEAKED_DISTRICT_ID) is None

    db_session.refresh(melde)
    db_session.refresh(ausweis)
    db_session.refresh(requirement)
    db_session.refresh(suggestion)
    db_session.refresh(locality)
    assert melde.jurisdiction_id == real_dresden_id
    assert ausweis.jurisdiction_id == real_dresden_id
    assert requirement.jurisdiction_id == real_dresden_id
    assert suggestion.jurisdiction_id == real_dresden_id
    assert locality.municipality_id == real_dresden_id
