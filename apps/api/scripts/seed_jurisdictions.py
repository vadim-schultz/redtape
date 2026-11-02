"""Idempotent seed: the DE, Saxony (SN) and Dresden (DD) jurisdictions.

Documents come from the discovery pipeline, not from this seed.

Run from `apps/api`:
  python -m scripts.seed_jurisdictions
"""

from __future__ import annotations

import uuid

from app.db import SessionLocal
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from sqlalchemy import select
from sqlalchemy.orm import Session

# Stable UUIDs (re-runs merge by primary key)
ID_DE = uuid.UUID("11111111-1111-1111-1111-111111111101")
ID_SN = uuid.UUID("11111111-1111-1111-1111-111111111102")
ID_DD = uuid.UUID("11111111-1111-1111-1111-111111111103")


def _find_or_create_jurisdiction(session: Session, placeholder: Jurisdiction) -> uuid.UUID:
    """Reuse a jurisdiction already at this (kind, code) instead of merging our own.

    A real location import (see import_openplz_locations.py) may already own this
    (kind, code) under a different id and parent -- e.g. a municipality is always
    parented under its district there, never flattened directly under its region
    the way this seed's own placeholder chain is. `uq_jurisdiction_kind_code` is
    the DB's own source of truth for uniqueness, so look up by the same pair
    rather than merge() by primary key and create a duplicate.
    """
    existing_id = session.execute(
        select(Jurisdiction.id).where(
            Jurisdiction.kind == placeholder.kind,
            Jurisdiction.code == placeholder.code,
        )
    ).scalar_one_or_none()
    if existing_id is not None:
        return existing_id

    session.merge(placeholder)
    return placeholder.id


def _country() -> Jurisdiction:
    return Jurisdiction(
        id=ID_DE,
        kind=JurisdictionKind.COUNTRY,
        geographic_parent_id=None,
        code="DE",
        administrative_roles=["COUNTRY"],
        name_i18n={"de": "Deutschland", "en": "Germany"},
    )


def _region(country_id: uuid.UUID) -> Jurisdiction:
    return Jurisdiction(
        id=ID_SN,
        kind=JurisdictionKind.REGION,
        geographic_parent_id=country_id,
        code="14",
        administrative_roles=["REGION"],
        name_i18n={"de": "Sachsen", "en": "Saxony"},
    )


def _municipality(region_id: uuid.UUID) -> Jurisdiction:
    return Jurisdiction(
        id=ID_DD,
        kind=JurisdictionKind.MUNICIPALITY,
        geographic_parent_id=region_id,
        code="14612000",
        administrative_roles=["DISTRICT", "MUNICIPALITY"],
        name_i18n={"de": "Dresden", "en": "Dresden"},
    )


def seed_jurisdictions(session: Session) -> None:
    """Upsert the DE, SN and DD jurisdictions (reusing real rows at the same kind and code)."""
    country_id = _find_or_create_jurisdiction(session, _country())
    session.flush()
    region_id = _find_or_create_jurisdiction(session, _region(country_id))
    session.flush()
    _find_or_create_jurisdiction(session, _municipality(region_id))
    session.flush()


def main() -> None:
    with SessionLocal() as session:
        seed_jurisdictions(session)
        session.commit()
    print("seed_jurisdictions: DE, SN and DD jurisdictions upserted.")


if __name__ == "__main__":
    main()
