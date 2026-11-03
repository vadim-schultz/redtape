"""One-off cleanup for the leaked pytest-fixture jurisdiction rows (finding C8).

A read-only check of the public API on 2026-11-02 found that production still
serves two pytest fixtures as real places: `GET /districts?state=14` returns
`146 Kreis Beispiel`, and `GET /cities?district=146` returns `14612
Musterstadt`. They are the fixtures from `tests/test_fix_saxony_jurisdiction_leak.py`
and `tests/test_locations_repository.py`; `scripts/fix_saxony_jurisdiction_leak.py`
names them as leaked.

Unlike that script's fake Dresden row, these two don't stand in for a real
place -- there is nothing to repoint onto. So anything that still references
them is leaked garbage too, and this script refuses to delete anything (on
either row) rather than guess what to do with it; read the dry-run report and
clean that up by hand first.

Dry-run by default (read-only). Pass --apply to delete the rows once nothing
references them. Idempotent: a second run after deletion reports both rows
absent and does nothing.
"""

from __future__ import annotations

import argparse
import uuid

from app.db import SessionLocal
from app.models.document import Document, DocumentRequirement
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.locality import Locality
from app.models.suggestion import Suggestion
from sqlalchemy import select
from sqlalchemy.orm import Session

LEAKED_DISTRICT_CODE = "146"
LEAKED_MUNICIPALITY_CODE = "14612"

# Every table with a FK that could point at a leaked jurisdiction row.
_JURISDICTION_REFERENCES = (
    (Document, Document.jurisdiction_id),
    (DocumentRequirement, DocumentRequirement.jurisdiction_id),
    (Suggestion, Suggestion.jurisdiction_id),
    (Locality, Locality.municipality_id),
)

RowReport = dict[str, bool | uuid.UUID | str | dict[str, int]]


class UnexpectedReferencesError(RuntimeError):
    """Raised when something still references a leaked row that --apply would delete."""


def _find_leaked_jurisdiction(session: Session, *, kind: JurisdictionKind, code: str) -> Jurisdiction | None:
    """Look up the leaked row by its `(kind, code)`, the DB's real uniqueness key."""
    return session.execute(
        select(Jurisdiction).where(Jurisdiction.kind == kind, Jurisdiction.code == code)
    ).scalar_one_or_none()


def _referencing_counts(session: Session, jurisdiction_id: uuid.UUID) -> dict[str, int]:
    """Count rows in every referencing table that point at `jurisdiction_id`."""
    counts: dict[str, int] = {}
    for model, column in _JURISDICTION_REFERENCES:
        rows = session.execute(select(column).where(column == jurisdiction_id)).scalars().all()
        counts[model.__tablename__] = len(rows)
    return counts


def inspect_leaked_jurisdictions(session: Session) -> dict[str, RowReport]:
    """Report the leaked district and municipality rows, and what still references them."""
    found = {
        "district": _find_leaked_jurisdiction(session, kind=JurisdictionKind.REGION, code=LEAKED_DISTRICT_CODE),
        "municipality": _find_leaked_jurisdiction(
            session, kind=JurisdictionKind.MUNICIPALITY, code=LEAKED_MUNICIPALITY_CODE
        ),
    }
    report: dict[str, RowReport] = {}
    for label, row in found.items():
        if row is None:
            report[label] = {"found": False}
            continue
        report[label] = {
            "found": True,
            "id": row.id,
            "code": row.code,
            "references": _referencing_counts(session, row.id),
        }
    return report


def remove_leaked_jurisdictions(session: Session, *, apply: bool) -> dict[str, RowReport]:
    """Report the leaked rows and, with `apply=True`, delete them.

    Refuses (raises `UnexpectedReferencesError`, deletes nothing) if any row
    still has a reference -- there is no real row to repoint onto, so an
    unexpected reference needs a human to look at it first.
    """
    report = inspect_leaked_jurisdictions(session)
    if not apply:
        return report

    for label, info in report.items():
        if info["found"] and any(info["references"].values()):  # type: ignore[union-attr]
            raise UnexpectedReferencesError(
                f"refusing to delete leaked {label} jurisdiction {info['id']}: still referenced by {info['references']}"
            )

    # geographic_parent_id is a RESTRICT self-FK: the municipality must go
    # before its parent district.
    for label in ("municipality", "district"):
        info = report[label]
        if info["found"]:
            session.execute(Jurisdiction.__table__.delete().where(Jurisdiction.id == info["id"]))
    session.commit()
    return report


def main() -> None:
    """Run the dry-run report, or delete the leaked rows with `--apply`."""
    parser = argparse.ArgumentParser(description="Remove the leaked pytest-fixture jurisdiction rows (finding C8).")
    parser.add_argument("--apply", action="store_true", help="Delete the rows; default is a read-only report.")
    args = parser.parse_args()

    session = SessionLocal()
    try:
        report = remove_leaked_jurisdictions(session, apply=args.apply)
        mode = "APPLY" if args.apply else "DRY RUN"
        print(f"[remove_leaked_fixture_jurisdictions] {mode}: {report}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
