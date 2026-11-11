"""Backfill ``candidate_search_text`` and embedding tasks for existing candidates.

Walks the candidates by id in batches, commits after each batch and calls the same
:meth:`SearchTextService.refresh_many` the write hooks use. Re-running changes nothing; ``--after`` resumes after
the last id a previous run printed. It stops cleanly when the database is at its soft limit.

``--locale <code>`` (repeatable) backfills translated locales instead: it reads the stored translation objects
and builds their search text and embedding tasks (see :mod:`scripts.backfill_search_locale`).
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass, field
from uuid import UUID

from app.db import SessionLocal
from app.features.discovery.budget_meter import ledger_meter
from app.features.discovery.budgets import BudgetService
from app.features.discovery.db_headroom import db_headroom
from app.features.discovery.repository import DiscoveryRepository
from app.features.search.repository import LengthStats, SearchTextRepository
from app.features.search.results import RefreshTotals
from app.features.search.service import SearchTextService
from app.features.search.text import TS_CONFIG_BY_LOCALE
from app.models.search import CANONICAL_LOCALE
from app.shared.object_store.provider import get_object_store
from sqlalchemy.orm import Session

from scripts.backfill_common import DEFAULT_BATCH_SIZE, Headroom, StopReason, room_stop
from scripts.backfill_search_locale import LocaleBackfillOptions, format_locale_report, run_locale_backfill

__all__ = ["DEFAULT_BATCH_SIZE", "Headroom", "StopReason"]

TRANSLATED_LOCALES = frozenset(TS_CONFIG_BY_LOCALE) - {CANONICAL_LOCALE}


@dataclass(frozen=True, slots=True)
class BackfillOptions:
    """Where to resume, how many candidates to refresh per commit and the translated locales to cover (none: German)."""

    after: UUID | None = None
    batch_size: int = DEFAULT_BATCH_SIZE
    locales: tuple[str, ...] = ()


@dataclass(slots=True)
class BackfillReport:
    """Counts of one run, where it stopped and the length statistics of the rows."""

    totals: RefreshTotals = field(default_factory=RefreshTotals)
    processed: int = 0
    last_id: UUID | None = None
    stopped: StopReason = StopReason.FINISHED
    lengths: LengthStats = LengthStats(0, 0, 0)


def run_backfill(session: Session, options: BackfillOptions, headroom: Headroom) -> BackfillReport:
    """Refresh every candidate after ``options.after``, one committed batch at a time."""
    repo, service = SearchTextRepository(session), SearchTextService.for_session(session)
    report = BackfillReport(last_id=options.after)
    while ids := repo.candidate_ids_after(report.last_id, options.batch_size):
        if not _has_room(headroom, report):
            break
        _refresh_batch(session, service, ids, report)
    report.lengths = repo.text_length_stats(CANONICAL_LOCALE)
    return report


def _has_room(headroom: Headroom, report: BackfillReport) -> bool:
    stop = room_stop(headroom)
    if stop is not None:
        report.stopped = stop
    return stop is None


def _refresh_batch(session: Session, service: SearchTextService, ids: Sequence[UUID], report: BackfillReport) -> None:
    totals = service.refresh_many(ids)
    session.commit()
    report.processed += len(ids)
    report.last_id = ids[-1]
    report.totals.merge(totals)


def format_report(report: BackfillReport) -> str:
    """Return the run as text: counts, where it stopped, and the text-length percentiles of the rows."""
    lengths, totals = report.lengths, report.totals
    lines = [
        f"processed={report.processed} written={totals.written} unchanged={totals.unchanged} "
        f"skipped_empty={totals.skipped_empty} enqueued={totals.enqueued}",
        f"search_text rows={lengths.rows} length p50={lengths.p50} p95={lengths.p95} chars",
        f"stopped={report.stopped.value} last_id={report.last_id}; resume with --after {report.last_id}",
    ]
    return "\n".join(lines)


def _parse_options(argv: Sequence[str] | None) -> BackfillOptions:
    parser = argparse.ArgumentParser(description="Backfill candidate search text and embedding tasks.")
    parser.add_argument("--after", type=UUID, default=None, help="resume after this candidate id")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help="candidates per commit")
    parser.add_argument(
        "--locale",
        action="append",
        default=[],
        choices=sorted(TRANSLATED_LOCALES),
        help="backfill this translated locale from its stored translations (repeatable); default: German text",
    )
    args = parser.parse_args(argv)
    return BackfillOptions(args.after, args.batch_size, tuple(args.locale))


def _backfill_locales(session: Session, options: BackfillOptions) -> None:
    """Backfill each translated locale from the ledger-metered object store and print one report per locale."""
    store = get_object_store(ledger_meter(BudgetService(DiscoveryRepository(session))))
    for locale in options.locales:
        locale_options = LocaleBackfillOptions(locale, options.after, options.batch_size)
        print(format_locale_report(run_locale_backfill(session, store, locale_options, db_headroom)))


def main(argv: Sequence[str] | None = None) -> int:
    """Run the backfill against the configured database and print its report."""
    options = _parse_options(argv)
    with SessionLocal() as session:
        if options.locales:
            _backfill_locales(session, options)
        else:
            print(format_report(run_backfill(session, options, db_headroom)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
