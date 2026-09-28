from __future__ import annotations

import uuid

import pytest
from app.models.document import Document, DocumentRequirement
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.locality import Locality
from app.models.suggestion import Suggestion, SuggestionKind, SuggestionSource
from scripts.cleanup_openplz_data import SuggestionsPresentError, wipe_all
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def _seed_tree(session: Session) -> uuid.UUID:
    country = Jurisdiction(kind=JurisdictionKind.COUNTRY, geographic_parent_id=None, code="DE")
    session.add(country)
    session.flush()
    region = Jurisdiction(kind=JurisdictionKind.REGION, geographic_parent_id=country.id, code="14")
    session.add(region)
    session.flush()
    municipality = Jurisdiction(kind=JurisdictionKind.MUNICIPALITY, geographic_parent_id=region.id, code="14612000")
    session.add(municipality)
    session.flush()
    return municipality.id


def _count(session: Session, model) -> int:
    return session.execute(select(func.count()).select_from(model)).scalar_one()


def test_wipe_all_deletes_documents_requirements_localities_and_jurisdictions(db_session: Session) -> None:
    municipality_id = _seed_tree(db_session)
    melde = Document(jurisdiction_id=municipality_id, slug="melde", title_i18n={"de": "x", "en": "x"})
    ausweis = Document(jurisdiction_id=municipality_id, slug="ausweis", title_i18n={"de": "y", "en": "y"})
    db_session.add_all([melde, ausweis])
    db_session.flush()
    db_session.add(
        DocumentRequirement(
            parent_document_id=melde.id, required_document_id=ausweis.id, jurisdiction_id=municipality_id
        )
    )
    db_session.add(Locality(municipality_id=municipality_id, postal_code="01001", name="Altstadt"))
    db_session.flush()

    counts = wipe_all(db_session, dry_run=False, include_suggestions=False)

    assert counts == {
        "document_requirement": 1,
        "document": 2,
        "suggestion": 0,
        "locality": 1,
        "jurisdiction": 3,
    }
    assert _count(db_session, Document) == 0
    assert _count(db_session, DocumentRequirement) == 0
    assert _count(db_session, Locality) == 0
    assert _count(db_session, Jurisdiction) == 0


def test_wipe_all_aborts_when_suggestions_present_without_flag(db_session: Session) -> None:
    municipality_id = _seed_tree(db_session)
    db_session.add(
        Suggestion(
            kind=SuggestionKind.NEW_DOCUMENT,
            source_type=SuggestionSource.HUMAN,
            jurisdiction_id=municipality_id,
            payload={"title_i18n": {"de": "x", "en": "x"}, "official_url": "https://example.com"},
        )
    )
    db_session.flush()

    with pytest.raises(SuggestionsPresentError):
        wipe_all(db_session, dry_run=False, include_suggestions=False)

    assert _count(db_session, Suggestion) == 1
    assert _count(db_session, Jurisdiction) == 3


def test_wipe_all_deletes_suggestions_when_flag_passed(db_session: Session) -> None:
    municipality_id = _seed_tree(db_session)
    db_session.add(
        Suggestion(
            kind=SuggestionKind.NEW_DOCUMENT,
            source_type=SuggestionSource.HUMAN,
            jurisdiction_id=municipality_id,
            payload={"title_i18n": {"de": "x", "en": "x"}, "official_url": "https://example.com"},
        )
    )
    db_session.flush()

    counts = wipe_all(db_session, dry_run=False, include_suggestions=True)

    assert counts["suggestion"] == 1
    assert _count(db_session, Suggestion) == 0
    assert _count(db_session, Jurisdiction) == 0


def test_wipe_all_dry_run_reports_counts_and_deletes_nothing(db_session: Session) -> None:
    _seed_tree(db_session)

    counts = wipe_all(db_session, dry_run=True, include_suggestions=False)

    assert counts["jurisdiction"] == 3
    assert _count(db_session, Jurisdiction) == 3


def test_wipe_all_is_safe_to_rerun_on_already_empty_tables(db_session: Session) -> None:
    counts = wipe_all(db_session, dry_run=False, include_suggestions=False)

    assert counts == {
        "document_requirement": 0,
        "document": 0,
        "suggestion": 0,
        "locality": 0,
        "jurisdiction": 0,
    }
