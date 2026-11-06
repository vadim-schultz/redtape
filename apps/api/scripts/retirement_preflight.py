"""Read-only preflight for the legacy taxonomy retirement.

Prints one JSON document with the row count and content checksum of every retired relation, the mention axis counts,
and the category backfill dry-run report. The whole run happens in a read-only transaction and writes nothing, so it
is safe to run against production before the retirement migration.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass

import sqlalchemy as sa
from app.db import engine
from sqlalchemy import Connection, Engine, text
from sqlalchemy.orm import Session

from scripts.category_backfill import BackfillReport, run_category_backfill
from scripts.legacy_taxonomy_archive import (
    ARCHIVED_SOURCES,
    RETIRED_TABLES,
    Fingerprint,
    MentionAxisProfile,
    fingerprint,
    mention_axis_profile,
)


class PreflightError(RuntimeError):
    """Raised when the database lacks the pre-retirement tables, so no report would be valid."""


@dataclass(frozen=True, slots=True)
class PreflightReport:
    """Everything the operator reviews before the retirement migration runs."""

    read_only: bool
    tables: dict[str, Fingerprint]
    mention_axes: MentionAxisProfile
    backfill_dry_run: BackfillReport


def run_preflight(db_engine: Engine) -> PreflightReport:
    """Run every preflight read inside one read-only transaction on ``db_engine``."""
    with db_engine.connect() as connection:
        connection.execute(text("SET TRANSACTION READ ONLY"))
        return _report(connection)


def _report(connection: Connection) -> PreflightReport:
    _require_legacy_tables(connection)
    return PreflightReport(
        read_only=_is_read_only(connection),
        tables={source.name: fingerprint(connection, source.select_sql) for source in ARCHIVED_SOURCES},
        mention_axes=mention_axis_profile(connection),
        backfill_dry_run=_dry_run(connection),
    )


def _require_legacy_tables(connection: Connection) -> None:
    """Refuse to report when a retired table is missing, rather than print zeros that look valid."""
    inspector = sa.inspect(connection)
    missing = [table for table in RETIRED_TABLES if not inspector.has_table(table)]
    if missing:
        raise PreflightError(f"preflight refused: missing legacy tables {', '.join(missing)}")


def _is_read_only(connection: Connection) -> bool:
    return str(connection.execute(text("SHOW transaction_read_only")).scalar_one()) == "on"


def _dry_run(connection: Connection) -> BackfillReport:
    with Session(bind=connection, autoflush=False) as session:
        return run_category_backfill(session, dry_run=True)


def main() -> None:
    """Print the preflight report as JSON, or exit 2 with the reason when the database is not pre-retirement."""
    try:
        report = run_preflight(engine)
    except PreflightError as error:
        print(error, file=sys.stderr)
        raise SystemExit(2) from error
    print(json.dumps(asdict(report), default=str, sort_keys=True))


if __name__ == "__main__":
    main()
