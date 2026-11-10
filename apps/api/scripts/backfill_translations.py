"""Backfill translation tasks for existing candidates.

Walks the candidates by id in batches, commits after each batch and calls the same
:meth:`TranslationEnqueuer.enqueue_many` the write hooks use, so only missing or stale translations are queued and a
re-run changes nothing. ``--after`` resumes after the last id a previous run printed and ``--locale`` limits the run
to one target locale. It stops cleanly when the database is at its soft limit.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass, field
from uuid import UUID

from app.db import SessionLocal
from app.features.discovery.db_headroom import db_headroom
from app.features.search.repository import SearchTextRepository
from app.features.translation.enqueue import TranslationEnqueuer
from app.features.translation.plan import EnqueueTotals
from sqlalchemy.orm import Session

from scripts.backfill_common import DEFAULT_BATCH_SIZE, Headroom, StopReason, room_stop

__all__ = ["StopReason"]


@dataclass(frozen=True, slots=True)
class BackfillOptions:
    """Where to resume, which locale to cover (all target locales when ``None``) and the candidates per commit."""

    after: UUID | None = None
    batch_size: int = DEFAULT_BATCH_SIZE
    locale: str | None = None


@dataclass(slots=True)
class BackfillReport:
    """Counts of one run and where it stopped."""

    totals: EnqueueTotals = field(default_factory=EnqueueTotals)
    processed: int = 0
    last_id: UUID | None = None
    stopped: StopReason = StopReason.FINISHED


def run_backfill(session: Session, options: BackfillOptions, headroom: Headroom) -> BackfillReport:
    """Queue the translations of every candidate after ``options.after``, one committed batch at a time."""
    locales = None if options.locale is None else [options.locale]
    enqueuer, candidates = TranslationEnqueuer(session, locales), SearchTextRepository(session)
    report = BackfillReport(last_id=options.after)
    while ids := candidates.candidate_ids_after(report.last_id, options.batch_size):
        if (stop := room_stop(headroom)) is not None:
            report.stopped = stop
            break
        _enqueue_batch(session, enqueuer, ids, report)
    return report


def _enqueue_batch(
    session: Session, enqueuer: TranslationEnqueuer, ids: Sequence[UUID], report: BackfillReport
) -> None:
    totals = enqueuer.enqueue_many(ids)
    session.commit()
    report.processed += len(ids)
    report.last_id = ids[-1]
    report.totals.merge(totals)


def format_report(report: BackfillReport) -> str:
    """Return the run as text: what was queued, what was already up to date or stale, and where to resume."""
    totals = report.totals
    lines = [
        f"processed={report.processed} enqueued={totals.enqueued} up_to_date={totals.up_to_date} "
        f"stale={totals.stale} missing={totals.missing} human_protected={totals.human_protected} "
        f"no_source={totals.no_source}",
        f"stopped={report.stopped.value} last_id={report.last_id}; resume with --after {report.last_id}",
    ]
    return "\n".join(lines)


def _parse_options(argv: Sequence[str] | None) -> BackfillOptions:
    parser = argparse.ArgumentParser(
        description="Backfill translation tasks for candidates without a current translation."
    )
    parser.add_argument("--after", type=UUID, default=None, help="resume after this candidate id")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help="candidates per commit")
    parser.add_argument("--locale", default=None, help="only this target locale (default: every target locale)")
    args = parser.parse_args(argv)
    return BackfillOptions(args.after, args.batch_size, args.locale)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the backfill against the configured database and print its report."""
    options = _parse_options(argv)
    with SessionLocal() as session:
        report = run_backfill(session, options, db_headroom)
    print(format_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
