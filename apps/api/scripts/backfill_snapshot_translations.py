"""Backfill snapshot translation tasks for existing procedure pages (chapter 09; an operator step after chapter 11).

Walks the catalogue rows that have a latest HTML snapshot, in id order, one batch at a time. For each page the rule in
:class:`SnapshotEnqueuer` names the locales to queue: every target locale of a page with candidates, and, for a page
without candidates, only the locales it is already translated into or has queued. A page with no candidates and no
translation costs nothing. Each batch
prints its missing, stale and current counts before it writes, and then commits. ``--after`` resumes after the last id a
previous run printed, ``--locale`` limits the run to one target locale, and ``--dry-run`` counts the pages and writes
nothing. It stops cleanly when the database is at its soft limit.
"""

from __future__ import annotations

import argparse
import enum
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from uuid import UUID

from app.db import SessionLocal
from app.features.discovery.db_headroom import db_headroom
from app.features.translation.plan import EnqueueTotals
from app.features.translation.snapshot_enqueue import SnapshotEnqueuer
from sqlalchemy.orm import Session

from scripts.backfill_common import DEFAULT_BATCH_SIZE, Headroom, StopReason, room_stop

__all__ = ["StopReason"]


class BackfillMode(enum.StrEnum):
    """Whether a run counts the pages it would queue, or queues them."""

    WRITE = "write"
    DRY_RUN = "dry_run"


@dataclass(frozen=True, slots=True)
class BackfillOptions:
    """Where to resume, which locale to cover (all target locales when ``None``), the pages per commit and the mode."""

    after: UUID | None = None
    batch_size: int = DEFAULT_BATCH_SIZE
    locale: str | None = None
    mode: BackfillMode = BackfillMode.WRITE


@dataclass(slots=True)
class BackfillReport:
    """Counts of one run and where it stopped."""

    totals: EnqueueTotals = field(default_factory=EnqueueTotals)
    processed: int = 0
    last_id: UUID | None = None
    stopped: StopReason = StopReason.FINISHED


def _quiet(_line: str) -> None:
    """Discard a progress line."""


def run_backfill(
    session: Session, options: BackfillOptions, headroom: Headroom, announce: Callable[[str], object] = _quiet
) -> BackfillReport:
    """Queue the snapshot translations of every page after ``options.after``, one committed batch at a time."""
    enqueuer = SnapshotEnqueuer(session, None if options.locale is None else (options.locale,))
    report = BackfillReport(last_id=options.after)
    while shas := enqueuer.pages_after(report.last_id, options.batch_size):
        if (stop := room_stop(headroom)) is not None:
            report.stopped = stop
            break
        _backfill_batch(session, enqueuer, shas, options.mode, report, announce)
    return report


def _backfill_batch(
    session: Session,
    enqueuer: SnapshotEnqueuer,
    shas: Mapping[UUID, str],
    mode: BackfillMode,
    report: BackfillReport,
    announce: Callable[[str], object],
) -> None:
    pages = enqueuer.load(shas)
    planned = enqueuer.count(pages, enqueuer.wanted_locales)
    announce(_batch_line(planned, len(pages)))
    if mode is BackfillMode.WRITE:
        planned = enqueuer.queue(pages, enqueuer.wanted_locales)
        session.commit()
    report.totals.merge(planned)
    report.processed += len(pages)
    report.last_id = list(shas)[-1]


def _batch_line(totals: EnqueueTotals, pages: int) -> str:
    return f"batch pages={pages} missing={totals.missing} stale={totals.stale} current={totals.up_to_date}"


def format_report(report: BackfillReport) -> str:
    """Return the run as text: what was queued, what was missing, stale or current, and where to resume."""
    totals = report.totals
    lines = [
        f"processed={report.processed} enqueued={totals.enqueued} missing={totals.missing} "
        f"stale={totals.stale} current={totals.up_to_date}",
        f"stopped={report.stopped.value} last_id={report.last_id}; resume with --after {report.last_id}",
    ]
    return "\n".join(lines)


def _parse_options(argv: Sequence[str] | None) -> BackfillOptions:
    parser = argparse.ArgumentParser(
        description="Backfill snapshot translation tasks for procedure pages that have a latest snapshot."
    )
    parser.add_argument("--after", type=UUID, default=None, help="resume after this catalogue row id")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help="catalogue rows per commit")
    parser.add_argument("--locale", default=None, help="only this target locale (default: every target locale)")
    parser.add_argument(
        "--dry-run", action="store_true", help="count the missing, stale and current pages and write nothing"
    )
    args = parser.parse_args(argv)
    mode = BackfillMode.DRY_RUN if args.dry_run else BackfillMode.WRITE
    return BackfillOptions(args.after, args.batch_size, args.locale, mode)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the backfill against the configured database and print its report."""
    options = _parse_options(argv)
    with SessionLocal() as session:
        report = run_backfill(session, options, db_headroom, announce=print)
    print(format_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
