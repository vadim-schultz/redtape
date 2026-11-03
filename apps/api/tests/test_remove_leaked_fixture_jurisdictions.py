from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.models.document import Document
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.locality import Locality
from scripts.remove_leaked_fixture_jurisdictions import (
    LEAKED_DISTRICT_CODE,
    LEAKED_MUNICIPALITY_CODE,
    UnexpectedReferencesError,
    remove_leaked_jurisdictions,
)
from sqlalchemy import select
from sqlalchemy.orm import Session


def _seed_leak(session: Session) -> tuple[uuid.UUID, uuid.UUID]:
    """Seed a copy of finding C8: the leaked `146`/`14612` fixture rows.

    Returns plain ids, not the ORM instances: `--apply` deletes rows through
    core `DELETE` statements the session doesn't know about, which would
    leave any returned instance expired and unsafe to read after a commit.
    """
    now = datetime.now(UTC)
    country = Jurisdiction(kind=JurisdictionKind.COUNTRY, geographic_parent_id=None, code="DE", last_updated=now)
    session.add(country)
    session.flush()
    sachsen = Jurisdiction(kind=JurisdictionKind.REGION, geographic_parent_id=country.id, code="14", last_updated=now)
    session.add(sachsen)
    session.flush()
    leaked_district = Jurisdiction(
        kind=JurisdictionKind.REGION,
        geographic_parent_id=sachsen.id,
        code=LEAKED_DISTRICT_CODE,
        administrative_roles=["DISTRICT"],
        name_i18n={"de": "Kreis Beispiel", "en": "Example District"},
        last_updated=now,
    )
    session.add(leaked_district)
    session.flush()
    leaked_municipality = Jurisdiction(
        kind=JurisdictionKind.MUNICIPALITY,
        geographic_parent_id=leaked_district.id,
        code=LEAKED_MUNICIPALITY_CODE,
        name_i18n={"de": "Musterstadt", "en": "Example City"},
        last_updated=now,
    )
    session.add(leaked_municipality)
    session.flush()
    return leaked_district.id, leaked_municipality.id


def test_dry_run_reports_found_rows_and_deletes_nothing(db_session: Session) -> None:
    district_id, municipality_id = _seed_leak(db_session)

    report = remove_leaked_jurisdictions(db_session, apply=False)

    assert report["district"]["found"] is True
    assert report["district"]["id"] == district_id
    assert report["municipality"]["found"] is True
    assert report["municipality"]["id"] == municipality_id
    assert db_session.get(Jurisdiction, district_id) is not None
    assert db_session.get(Jurisdiction, municipality_id) is not None


def test_dry_run_reports_absent_when_rows_are_gone(db_session: Session) -> None:
    report = remove_leaked_jurisdictions(db_session, apply=False)

    assert report == {
        "district": {"found": False},
        "municipality": {"found": False},
    }


def test_apply_deletes_the_leaked_rows_when_nothing_references_them(db_session: Session) -> None:
    district_id, municipality_id = _seed_leak(db_session)

    report = remove_leaked_jurisdictions(db_session, apply=True)

    assert report["district"]["found"] is True
    assert report["municipality"]["found"] is True
    assert db_session.get(Jurisdiction, district_id) is None
    assert db_session.get(Jurisdiction, municipality_id) is None


def test_apply_is_idempotent_on_second_run(db_session: Session) -> None:
    _seed_leak(db_session)
    remove_leaked_jurisdictions(db_session, apply=True)

    second_report = remove_leaked_jurisdictions(db_session, apply=True)

    assert second_report == {
        "district": {"found": False},
        "municipality": {"found": False},
    }


def test_apply_refuses_when_something_references_the_leaked_rows(db_session: Session) -> None:
    district_id, municipality_id = _seed_leak(db_session)
    doc = Document(jurisdiction_id=municipality_id, slug="fake-doc", title_i18n={"de": "x", "en": "x"})
    db_session.add(doc)
    db_session.flush()
    doc_id = doc.id

    try:
        remove_leaked_jurisdictions(db_session, apply=True)
        raised = False
    except UnexpectedReferencesError:
        raised = True

    assert raised is True
    assert db_session.get(Jurisdiction, district_id) is not None
    assert db_session.get(Jurisdiction, municipality_id) is not None
    assert db_session.execute(select(Document).where(Document.id == doc_id)).scalar_one_or_none() is not None


def test_apply_deletes_only_the_leaked_rows_when_one_is_blocked(db_session: Session) -> None:
    district_id, municipality_id = _seed_leak(db_session)
    locality = Locality(municipality_id=municipality_id, postal_code="14612", name="Musterstadt")
    db_session.add(locality)
    db_session.flush()

    try:
        remove_leaked_jurisdictions(db_session, apply=True)
        raised = False
    except UnexpectedReferencesError:
        raised = True

    assert raised is True
    # Refusing is all-or-nothing: the district, which has no references of its
    # own, is still left alone rather than deleted out from under the blocked
    # municipality's parent.
    assert db_session.get(Jurisdiction, district_id) is not None
    assert db_session.get(Jurisdiction, municipality_id) is not None
