"""Clean up OpenPLZ-derived jurisdiction and locality rows, or wipe the location tables entirely."""

from __future__ import annotations

import argparse
import uuid
from datetime import UTC, datetime

from app.db import SessionLocal
from app.models.document import Document, DocumentRequirement
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.locality import Locality
from app.models.suggestion import Suggestion
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from scripts.openplz_ids import country_id, locality_id, municipality_id, region_id


class SuggestionsPresentError(RuntimeError):
    """Raised by wipe_all() when suggestion rows exist and --include-suggestions wasn't passed."""


def _expected_jurisdiction_id(kind: JurisdictionKind, code: str | None) -> uuid.UUID | None:
    """
    Compute the deterministic UUID the OpenPLZ import would generate for this row.

    We only mark a row as "OpenPLZ-derived" when its existing `id` matches the expected UUID.
    This avoids accidentally deleting non-OpenPLZ data that might share schema tables.
    """
    if code is None:
        return None

    if kind == JurisdictionKind.COUNTRY:
        return country_id(code)
    if kind == JurisdictionKind.REGION:
        return region_id(code)
    if kind == JurisdictionKind.MUNICIPALITY:
        return municipality_id(code)

    # Future-proofing: unknown kind.
    return None


def _compute_openplz_ids(session) -> tuple[list[uuid.UUID], list[uuid.UUID]]:
    """Return the jurisdiction and locality ids whose stored id equals the deterministic OpenPLZ id."""
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
        expected_locality_id = locality_id(muni_code, postal_code, name)
        if loc_id == expected_locality_id:
            openplz_locality_ids.append(loc_id)

    return openplz_jurisdiction_ids, openplz_locality_ids


def cleanup_openplz_data(*, dry_run: bool) -> None:
    """Delete the OpenPLZ-derived localities, municipalities, regions and countries, leaf first.

    Rows whose id is not the deterministic OpenPLZ id are left alone. A dry run prints the counts and rolls back.
    """
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


def _count(session: Session, model) -> int:
    return session.execute(select(func.count()).select_from(model)).scalar_one()


def _delete_all(session: Session, model) -> None:
    session.execute(model.__table__.delete())


def _delete_jurisdictions_leaf_first(session: Session) -> None:
    # geographic_parent_id is a non-deferrable RESTRICT self-FK, so children
    # must go before parents -- a single bulk DELETE can't guarantee that.
    for kind in (JurisdictionKind.MUNICIPALITY, JurisdictionKind.REGION, JurisdictionKind.COUNTRY):
        session.execute(Jurisdiction.__table__.delete().where(Jurisdiction.kind == kind))


def _guard_suggestions_present(suggestion_count: int, include_suggestions: bool) -> None:
    if suggestion_count and not include_suggestions:
        raise SuggestionsPresentError(
            f"{suggestion_count} suggestion row(s) exist; pass --include-suggestions to delete "
            "them, or inspect/migrate them first."
        )


def _wipe_all_counts(session: Session, *, suggestion_count: int, include_suggestions: bool) -> dict[str, int]:
    return {
        "document_requirement": _count(session, DocumentRequirement),
        "document": _count(session, Document),
        "suggestion": suggestion_count if include_suggestions else 0,
        "locality": _count(session, Locality),
        "jurisdiction": _count(session, Jurisdiction),
    }


def _delete_all_wipe_all_rows(session: Session, *, include_suggestions: bool) -> None:
    _delete_all(session, DocumentRequirement)
    _delete_all(session, Document)
    if include_suggestions:
        _delete_all(session, Suggestion)
    _delete_all(session, Locality)
    _delete_jurisdictions_leaf_first(session)


def wipe_all(session: Session, *, dry_run: bool, include_suggestions: bool) -> dict[str, int]:
    """
    Delete every row from the OpenPLZ location tables and their dependents.

    Aborts before deleting anything if `suggestion` has rows and
    `include_suggestions` wasn't passed -- that table's real-world contents
    (possible user-submitted data) aren't OpenPLZ-derived, so it's treated
    conservatively by default rather than assumed disposable.
    """
    suggestion_count = _count(session, Suggestion)
    _guard_suggestions_present(suggestion_count, include_suggestions)
    counts = _wipe_all_counts(session, suggestion_count=suggestion_count, include_suggestions=include_suggestions)

    if not dry_run:
        _delete_all_wipe_all_rows(session, include_suggestions=include_suggestions)
        session.commit()

    return counts


def _run_wipe_all(*, dry_run: bool, include_suggestions: bool) -> None:
    session = SessionLocal()
    try:
        counts = wipe_all(session, dry_run=dry_run, include_suggestions=include_suggestions)
        prefix = "[cleanup_openplz_data] DRY RUN (wipe-all)" if dry_run else "[cleanup_openplz_data] wipe-all"
        print(f"{prefix}: {counts}")
    finally:
        session.close()


def main() -> None:
    """Parse the command-line flags and run either the wipe-all or the derived-row cleanup."""
    parser = argparse.ArgumentParser(description="Cleanup OpenPLZ-derived jurisdiction + locality data.")
    parser.add_argument(
        "--wipe-all",
        action="store_true",
        help=(
            "Delete all rows from document_requirement, document, locality and jurisdiction "
            "(start from scratch for the OpenPLZ hierarchy + MVP seed content). Aborts if "
            "suggestion has rows, unless --include-suggestions is also passed."
        ),
    )
    parser.add_argument(
        "--include-suggestions",
        action="store_true",
        help="With --wipe-all, also delete suggestion rows instead of aborting if any exist.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute what would be deleted, but do not modify the DB.",
    )
    args = parser.parse_args()

    if args.wipe_all:
        _run_wipe_all(dry_run=args.dry_run, include_suggestions=args.include_suggestions)
    else:
        cleanup_openplz_data(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
