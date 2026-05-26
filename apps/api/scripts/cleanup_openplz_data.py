from __future__ import annotations

import argparse
import uuid
from datetime import UTC, datetime

from app.db import SessionLocal
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.locality import Locality
from sqlalchemy import select

UUID_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "redtape-openplz")


def _stable_uuid(key: str) -> uuid.UUID:
    # Deterministic UUID so re-imports are idempotent.
    return uuid.uuid5(UUID_NAMESPACE, key)


def _expected_jurisdiction_id(kind: JurisdictionKind, code: str | None) -> uuid.UUID | None:
    """
    Compute the deterministic UUID the OpenPLZ import would generate for this row.

    We only mark a row as "OpenPLZ-derived" when its existing `id` matches the expected UUID.
    This avoids accidentally deleting non-OpenPLZ data that might share schema tables.
    """

    if code is None:
        return None

    if kind == JurisdictionKind.COUNTRY:
        return _stable_uuid(f"jurisdiction:COUNTRY:{code}")
    if kind == JurisdictionKind.REGION:
        return _stable_uuid(f"jurisdiction:REGION:{code}")
    if kind == JurisdictionKind.MUNICIPALITY:
        return _stable_uuid(f"jurisdiction:MUNICIPALITY:{code}")

    # Future-proofing: unknown kind.
    return None


def _compute_openplz_ids(session) -> tuple[list[uuid.UUID], list[uuid.UUID]]:
    """
    Return (jurisdiction_ids, locality_ids) that appear to be OpenPLZ-derived.
    """

    openplz_jurisdiction_ids: list[uuid.UUID] = []
    jurisdiction_rows = session.execute(select(Jurisdiction.id, Jurisdiction.kind, Jurisdiction.code)).all()
    for jid, kind, code in jurisdiction_rows:
        expected = _expected_jurisdiction_id(kind, code)
        if expected is not None and jid == expected:
            openplz_jurisdiction_ids.append(jid)

    # Localities require looking up their municipality code to compute the deterministic UUID.
    openplz_locality_ids: list[uuid.UUID] = []
    locality_rows = session.execute(
        select(
            Locality.id,
            Locality.postal_code,
            Locality.name,
            Jurisdiction.code,
        ).join(Jurisdiction, Locality.municipality_id == Jurisdiction.id)
    ).all()

    for loc_id, postal_code, name, muni_code in locality_rows:
        if muni_code is None:
            continue
        expected_locality_id = _stable_uuid(f"locality:{muni_code}:{postal_code}:{name}")
        if loc_id == expected_locality_id:
            openplz_locality_ids.append(loc_id)

    return openplz_jurisdiction_ids, openplz_locality_ids


def cleanup_openplz_data(*, dry_run: bool) -> None:
    session = SessionLocal()
    try:
        now = datetime.now(UTC)
        jurisdiction_ids, locality_ids = _compute_openplz_ids(session)

        # Determine deletion order due to FK constraints on jurisdiction.geographic_parent_id.
        # 1) Locality (FK -> municipality jurisdiction)
        # 2) Municipalities (FK -> districts/states regions)
        # 3) Regions (FK -> country)
        # 4) Country (root)
        muni_ids = (
            session.execute(
                select(Jurisdiction.id).where(
                    Jurisdiction.id.in_(jurisdiction_ids),
                    Jurisdiction.kind == JurisdictionKind.MUNICIPALITY,
                )
            )
            .scalars()
            .all()
        )

        region_ids = (
            session.execute(
                select(Jurisdiction.id).where(
                    Jurisdiction.id.in_(jurisdiction_ids),
                    Jurisdiction.kind == JurisdictionKind.REGION,
                )
            )
            .scalars()
            .all()
        )

        country_ids = (
            session.execute(
                select(Jurisdiction.id).where(
                    Jurisdiction.id.in_(jurisdiction_ids),
                    Jurisdiction.kind == JurisdictionKind.COUNTRY,
                )
            )
            .scalars()
            .all()
        )

        print(f"[cleanup_openplz_data] started_at={now.isoformat()}")
        print(
            f"[cleanup_openplz_data] openplz_jurisdictions={len(jurisdiction_ids)} "
            f"openplz_localities={len(locality_ids)}"
        )

        if dry_run:
            print("[cleanup_openplz_data] DRY RUN: no data will be deleted.")
            session.rollback()
            return

        # Use a transaction: if something goes wrong, rollback to keep DB consistent.
        # (SQLAlchemy session is already transactional; commit only at end.)
        if locality_ids:
            session.execute(Locality.__table__.delete().where(Locality.id.in_(locality_ids)))
            print(f"[cleanup_openplz_data] deleted_localities={len(locality_ids)}")

        if muni_ids:
            session.execute(Jurisdiction.__table__.delete().where(Jurisdiction.id.in_(muni_ids)))
            print(f"[cleanup_openplz_data] deleted_municipalities={len(muni_ids)}")

        if region_ids:
            session.execute(Jurisdiction.__table__.delete().where(Jurisdiction.id.in_(region_ids)))
            print(f"[cleanup_openplz_data] deleted_regions={len(region_ids)}")

        if country_ids:
            session.execute(Jurisdiction.__table__.delete().where(Jurisdiction.id.in_(country_ids)))
            print(f"[cleanup_openplz_data] deleted_countries={len(country_ids)}")

        session.commit()
        print("[cleanup_openplz_data] commit complete.")
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Cleanup OpenPLZ-derived jurisdiction + locality data.")
    parser.add_argument(
        "--wipe-all",
        action="store_true",
        help=(
            "Delete all rows from locality + jurisdiction (start from scratch for the OpenPLZ hierarchy). "
            "Use only if these tables contain exclusively OpenPLZ-derived data."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute what would be deleted, but do not modify the DB.",
    )
    args = parser.parse_args()

    if args.wipe_all:
        # Wipe mode: remove the entire OpenPLZ hierarchy tables regardless of id matching.
        # FK safety: delete localities first, then jurisdictions.
        session = SessionLocal()
        try:
            if args.dry_run:
                print("[cleanup_openplz_data] DRY RUN (wipe-all): would delete all rows in locality + jurisdiction")
                session.rollback()
            else:
                session.execute(Locality.__table__.delete())
                session.execute(Jurisdiction.__table__.delete())
                session.commit()
                print("[cleanup_openplz_data] wipe-all complete (locality + jurisdiction).")
        finally:
            session.close()
    else:
        cleanup_openplz_data(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
