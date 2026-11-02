from __future__ import annotations

from app.models.document import Document, DocumentRequirement
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from scripts.seed_jurisdictions import seed_jurisdictions
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def _real_country(session: Session) -> Jurisdiction:
    """A jurisdiction row shaped like the real OpenPLZ import's DE (a different id)."""
    country = Jurisdiction(kind=JurisdictionKind.COUNTRY, geographic_parent_id=None, code="DE")
    session.add(country)
    session.flush()
    return country


def test_reuses_an_existing_country_row_instead_of_duplicating_it(db_session: Session) -> None:
    real_country = _real_country(db_session)

    seed_jurisdictions(db_session)
    db_session.flush()

    rows = db_session.scalars(
        select(Jurisdiction).where(Jurisdiction.geographic_parent_id.is_(None), Jurisdiction.code == "DE")
    ).all()
    assert [r.id for r in rows] == [real_country.id]


def test_reuses_an_existing_region_row_instead_of_duplicating_it(db_session: Session) -> None:
    real_country = _real_country(db_session)
    real_region = Jurisdiction(kind=JurisdictionKind.REGION, geographic_parent_id=real_country.id, code="14")
    db_session.add(real_region)
    db_session.flush()

    seed_jurisdictions(db_session)
    db_session.flush()

    rows = db_session.scalars(
        select(Jurisdiction).where(Jurisdiction.geographic_parent_id == real_country.id, Jurisdiction.code == "14")
    ).all()
    assert [r.id for r in rows] == [real_region.id]


def test_reuses_a_real_municipality_found_by_kind_and_code(db_session: Session) -> None:
    # Shaped like the real OpenPLZ import: Dresden (a kreisfreie Stadt) is its own
    # district, and the municipality row sits under that district, not directly
    # under the region. `seed_jurisdictions` must find it by (kind, code) rather than
    # assuming a flat region -> municipality parent chain.
    real_country = _real_country(db_session)
    real_region = Jurisdiction(kind=JurisdictionKind.REGION, geographic_parent_id=real_country.id, code="14")
    db_session.add(real_region)
    db_session.flush()
    real_district = Jurisdiction(
        kind=JurisdictionKind.REGION,
        geographic_parent_id=real_region.id,
        code="14612",
        administrative_roles=["DISTRICT"],
    )
    db_session.add(real_district)
    db_session.flush()
    real_dresden = Jurisdiction(
        kind=JurisdictionKind.MUNICIPALITY,
        geographic_parent_id=real_district.id,
        code="14612000",
    )
    db_session.add(real_dresden)
    db_session.flush()

    seed_jurisdictions(db_session)
    db_session.flush()

    municipality_rows = db_session.scalars(
        select(Jurisdiction).where(
            Jurisdiction.kind == JurisdictionKind.MUNICIPALITY,
            Jurisdiction.code == "14612000",
        )
    ).all()
    assert [r.id for r in municipality_rows] == [real_dresden.id]


def test_creates_its_own_placeholder_hierarchy_on_a_fresh_database(db_session: Session) -> None:
    seed_jurisdictions(db_session)
    db_session.flush()

    country_rows = db_session.scalars(
        select(Jurisdiction).where(Jurisdiction.geographic_parent_id.is_(None), Jurisdiction.code == "DE")
    ).all()
    assert len(country_rows) == 1


def test_rerunning_does_not_create_duplicate_jurisdictions(db_session: Session) -> None:
    seed_jurisdictions(db_session)
    db_session.flush()
    seed_jurisdictions(db_session)
    db_session.flush()

    country_rows = db_session.scalars(
        select(Jurisdiction).where(Jurisdiction.geographic_parent_id.is_(None), Jurisdiction.code == "DE")
    ).all()
    assert len(country_rows) == 1


def test_creates_no_document_or_requirement_rows(db_session: Session) -> None:
    seed_jurisdictions(db_session)
    db_session.flush()

    documents = db_session.scalar(select(func.count()).select_from(Document))
    requirements = db_session.scalar(select(func.count()).select_from(DocumentRequirement))
    assert (documents, requirements) == (0, 0)
