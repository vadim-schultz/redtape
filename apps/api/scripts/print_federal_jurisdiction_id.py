"""Print the Germany country jurisdiction UUID for ``FEDERAL_JURISDICTION_ID``.

Run from ``apps/api`` (uses ``DATABASE_URL`` from the environment):

  python -m scripts.print_federal_jurisdiction_id

Matches production canon: ``kind = COUNTRY`` and ``code = DE``. After OpenPLZ import
the id may differ from the seed placeholder — always read it from the database.
"""

from __future__ import annotations

import sys

from app.db import SessionLocal
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from sqlalchemy import select


def main() -> None:
    """Look up DE country ``jurisdiction.id`` and print it on stdout."""
    with SessionLocal() as session:
        jurisdiction_id = session.execute(
            select(Jurisdiction.id).where(
                Jurisdiction.kind == JurisdictionKind.COUNTRY,
                Jurisdiction.code == "DE",
            )
        ).scalar_one_or_none()
    if jurisdiction_id is None:
        print(
            "print_federal_jurisdiction_id: no jurisdiction with kind=COUNTRY, code=DE",
            file=sys.stderr,
        )
        sys.exit(1)
    print(jurisdiction_id)


if __name__ == "__main__":
    main()
