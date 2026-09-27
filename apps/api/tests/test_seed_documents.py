from __future__ import annotations

from app.models.document import Document
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from scripts.seed_documents import seed_mvp_graph
from sqlalchemy import select
from sqlalchemy.orm import Session


def _real_country(session: Session) -> Jurisdiction:
    """A jurisdiction row shaped like the real OpenPLZ import's DE (a different id)."""
    country = Jurisdiction(kind=JurisdictionKind.COUNTRY, geographic_parent_id=None, code="DE")
    session.add(country)
    session.flush()
    return country


def test_reuses_an_existing_country_row_instead_of_duplicating_it(db_session: Session) -> None:
    real_country = _real_country(db_session)

    seed_mvp_graph(db_session)
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

    seed_mvp_graph(db_session)
    db_session.flush()

    rows = db_session.scalars(
        select(Jurisdiction).where(Jurisdiction.geographic_parent_id == real_country.id, Jurisdiction.code == "14")
    ).all()
    assert [r.id for r in rows] == [real_region.id]


def test_documents_are_scoped_under_the_real_hierarchy_when_it_already_exists(db_session: Session) -> None:
    real_country = _real_country(db_session)
    real_region = Jurisdiction(kind=JurisdictionKind.REGION, geographic_parent_id=real_country.id, code="14")
    db_session.add(real_region)
    db_session.flush()

    seed_mvp_graph(db_session)
    db_session.flush()

    dresden = db_session.scalars(
        select(Jurisdiction).where(Jurisdiction.geographic_parent_id == real_region.id, Jurisdiction.code == "14612000")
    ).one()
    documents = db_session.scalars(select(Document).where(Document.jurisdiction_id == dresden.id)).all()
    assert len(documents) == 4


def test_creates_its_own_placeholder_hierarchy_on_a_fresh_database(db_session: Session) -> None:
    seed_mvp_graph(db_session)
    db_session.flush()

    country_rows = db_session.scalars(
        select(Jurisdiction).where(Jurisdiction.geographic_parent_id.is_(None), Jurisdiction.code == "DE")
    ).all()
    assert len(country_rows) == 1


def test_rerunning_does_not_create_duplicate_jurisdictions(db_session: Session) -> None:
    seed_mvp_graph(db_session)
    db_session.flush()
    seed_mvp_graph(db_session)
    db_session.flush()

    country_rows = db_session.scalars(
        select(Jurisdiction).where(Jurisdiction.geographic_parent_id.is_(None), Jurisdiction.code == "DE")
    ).all()
    assert len(country_rows) == 1
