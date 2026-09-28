from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from scripts.import_openplz_locations import upsert_jurisdiction
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
