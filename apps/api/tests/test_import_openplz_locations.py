from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.locality import Locality
from scripts.import_openplz_locations import upsert_jurisdiction, upsert_locality
from sqlalchemy.orm import Session


def _touched_at() -> datetime:
    return datetime.now(UTC)


def test_upsert_jurisdiction_inserts_when_no_existing_row(db_session: Session) -> None:
    new_id = uuid.uuid4()

    result = upsert_jurisdiction(
        db_session,
        jurisdiction_id=new_id,
        kind=JurisdictionKind.COUNTRY,
        geographic_parent_id=None,
        code="DE",
        openplz_type="Country",
        name_de="Deutschland",
        administrative_roles=["COUNTRY"],
        touched_at=_touched_at(),
    )
    db_session.flush()

    assert result.id == new_id
    assert db_session.get(Jurisdiction, new_id).code == "DE"


def test_upsert_jurisdiction_updates_in_place_when_kind_code_matches_under_same_parent(
    db_session: Session,
) -> None:
    parent = Jurisdiction(kind=JurisdictionKind.COUNTRY, geographic_parent_id=None, code="DE")
    db_session.add(parent)
    db_session.flush()
    existing = Jurisdiction(
        kind=JurisdictionKind.REGION,
        geographic_parent_id=parent.id,
        code="14",
        name_i18n={"de": "Sachsen", "en": "Sachsen"},
    )
    db_session.add(existing)
    db_session.flush()
    existing_id = existing.id

    result = upsert_jurisdiction(
        db_session,
        jurisdiction_id=uuid.uuid4(),
        kind=JurisdictionKind.REGION,
        geographic_parent_id=parent.id,
        code="14",
        openplz_type=None,
        name_de="Sachsen",
        administrative_roles=["REGION"],
        touched_at=_touched_at(),
    )
    db_session.flush()

    assert result.id == existing_id


def test_upsert_jurisdiction_reparents_existing_row_when_kind_code_matches_under_different_parent(
    db_session: Session,
) -> None:
    # Simulates a leftover/leaked row parented incorrectly (e.g. flattened
    # directly under the region instead of nested under its real district).
    parent_a = Jurisdiction(kind=JurisdictionKind.REGION, geographic_parent_id=None, code="14")
    db_session.add(parent_a)
    db_session.flush()
    parent_b = Jurisdiction(kind=JurisdictionKind.REGION, geographic_parent_id=None, code="146")
    db_session.add(parent_b)
    db_session.flush()

    stale = Jurisdiction(
        kind=JurisdictionKind.MUNICIPALITY,
        geographic_parent_id=parent_a.id,
        code="14612000",
        name_i18n={"de": "Dresden (stale)", "en": "Dresden (stale)"},
    )
    db_session.add(stale)
    db_session.flush()
    stale_id = stale.id

    result = upsert_jurisdiction(
        db_session,
        jurisdiction_id=uuid.uuid4(),
        kind=JurisdictionKind.MUNICIPALITY,
        geographic_parent_id=parent_b.id,
        code="14612000",
        openplz_type="Kreisfreie Stadt",
        name_de="Dresden",
        administrative_roles=["MUNICIPALITY", "DISTRICT"],
        touched_at=_touched_at(),
    )
    db_session.flush()

    assert result.id == stale_id
    assert result.geographic_parent_id == parent_b.id
    assert result.name_i18n["de"] == "Dresden"


def _seed_municipality(session: Session, *, code: str, region_code: str = "14") -> uuid.UUID:
    region = Jurisdiction(kind=JurisdictionKind.REGION, geographic_parent_id=None, code=region_code)
    session.add(region)
    session.flush()
    municipality = Jurisdiction(kind=JurisdictionKind.MUNICIPALITY, geographic_parent_id=region.id, code=code)
    session.add(municipality)
    session.flush()
    return municipality.id


def test_upsert_locality_inserts_when_no_existing_row(db_session: Session) -> None:
    municipality_id = _seed_municipality(db_session, code="14511000")
    new_id = uuid.uuid4()

    result = upsert_locality(
        db_session,
        locality_id=new_id,
        municipality_id=municipality_id,
        postal_code="09111",
        name="Chemnitz",
        touched_at=_touched_at(),
    )
    db_session.flush()

    assert result.id == new_id


def test_upsert_locality_updates_in_place_when_id_matches(db_session: Session) -> None:
    municipality_id = _seed_municipality(db_session, code="14511000")
    locality_id = uuid.uuid4()
    existing = Locality(id=locality_id, municipality_id=municipality_id, postal_code="09111", name="Chemnitz")
    db_session.add(existing)
    db_session.flush()

    result = upsert_locality(
        db_session,
        locality_id=locality_id,
        municipality_id=municipality_id,
        postal_code="09111",
        name="Chemnitz",
        touched_at=_touched_at(),
    )
    db_session.flush()

    assert result.id == locality_id


def test_upsert_locality_reparents_existing_row_when_municipality_id_changed(db_session: Session) -> None:
    # Simulates a municipality jurisdiction row that got reparented/self-healed
    # (see upsert_jurisdiction) without changing its own id -- a locality's
    # deterministic id is independent of municipality_id, so a stale
    # (municipality_id, postal_code, name) lookup misses the existing row and
    # would otherwise try to INSERT a duplicate primary key.
    old_municipality_id = _seed_municipality(db_session, code="14511000", region_code="14")
    new_municipality_id = _seed_municipality(db_session, code="14511999", region_code="146")
    locality_id = uuid.uuid4()
    existing = Locality(
        id=locality_id, municipality_id=old_municipality_id, postal_code="09111", name="Chemnitz"
    )
    db_session.add(existing)
    db_session.flush()

    result = upsert_locality(
        db_session,
        locality_id=locality_id,
        municipality_id=new_municipality_id,
        postal_code="09111",
        name="Chemnitz",
        touched_at=_touched_at(),
    )
    db_session.flush()

    assert result.id == locality_id
    assert result.municipality_id == new_municipality_id
