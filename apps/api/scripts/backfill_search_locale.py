"""Backfill the search text and embedding tasks of one translated locale from its stored translation objects.

Walks the index rows of the locale by candidate id in batches, reads each object (one metered Class B read), and
calls the same :meth:`SearchTextService.refresh_locale` the translation-stored subscriber uses. Re-running changes
nothing. An index row whose object is missing or invalid is reported and skipped. The run stops cleanly when the
database is at its soft limit or the object store refuses a read.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from uuid import UUID

from app.features.search.results import RefreshStatus, RefreshTotals
from app.features.search.service import SearchTextService
from app.features.translation.repository import IndexedObject, TranslationRepository
from app.features.translation.store import (
    TranslationObjectInvalidError,
    TranslationObjectMissingError,
    TranslationStore,
)
from app.shared.object_store import ObjectStore, ObjectStoreUnavailableError
from sqlalchemy.orm import Session

from scripts.backfill_common import DEFAULT_BATCH_SIZE, Headroom, StopReason, room_stop

MAX_LISTED = 20
"""Unreadable candidates the report lists; the count always covers all of them."""


@dataclass(frozen=True, slots=True)
class LocaleBackfillOptions:
    """The locale to cover, where to resume and how many translations to refresh per commit."""

    locale: str
    after: UUID | None = None
    batch_size: int = DEFAULT_BATCH_SIZE


@dataclass(slots=True)
class LocaleBackfillReport:
    """Counts of one locale's run, the candidates whose object could not be read, and where it stopped."""

    locale: str
    totals: RefreshTotals = field(default_factory=RefreshTotals)
    processed: int = 0
    last_id: UUID | None = None
    stopped: StopReason = StopReason.FINISHED
    unreadable: list[UUID] = field(default_factory=list)


def run_locale_backfill(
    session: Session, backend: ObjectStore | None, options: LocaleBackfillOptions, headroom: Headroom
) -> LocaleBackfillReport:
    """Refresh the search text of every stored translation of ``options.locale``, one committed batch at a time."""
    index, service = TranslationRepository(session), SearchTextService.for_session(session)
    report = LocaleBackfillReport(options.locale, last_id=options.after)
    store = TranslationStore(backend)
    while refs := index.indexed_after(options.locale, report.last_id, options.batch_size):
        if (stop := room_stop(headroom)) is not None:
            report.stopped = stop
            break
        _refresh_batch(session, service, store, refs, report)
        if report.stopped is not StopReason.FINISHED:
            break
    return report


def _refresh_batch(
    session: Session,
    service: SearchTextService,
    store: TranslationStore,
    refs: Sequence[IndexedObject],
    report: LocaleBackfillReport,
) -> None:
    try:
        for ref in refs:
            _refresh_one(service, store, ref, report)
    except ObjectStoreUnavailableError:
        report.stopped = StopReason.STORE_UNAVAILABLE
    session.commit()


def _refresh_one(
    service: SearchTextService, store: TranslationStore, ref: IndexedObject, report: LocaleBackfillReport
) -> None:
    try:
        payload = store.read(ref.storage_key)
    except (TranslationObjectMissingError, TranslationObjectInvalidError):
        report.totals.counts[RefreshStatus.OBJECT_UNREADABLE] += 1
        report.unreadable.append(ref.candidate_id)
    else:
        report.totals.add(service.refresh_locale(ref.candidate_id, report.locale, payload))
    report.processed += 1
    report.last_id = ref.candidate_id


def format_locale_report(report: LocaleBackfillReport) -> str:
    """Return the run as text: counts, the unreadable objects, and where to resume."""
    totals = report.totals
    lines = [
        f"locale={report.locale} processed={report.processed} written={totals.written} "
        f"unchanged={totals.unchanged} skipped_empty={totals.skipped_empty} enqueued={totals.enqueued} "
        f"object_unreadable={totals.object_unreadable}",
        *(f"unreadable candidate_id={candidate_id}" for candidate_id in report.unreadable[:MAX_LISTED]),
        f"stopped={report.stopped.value} last_id={report.last_id}; resume with --locale {report.locale} "
        f"--after {report.last_id}",
    ]
    return "\n".join(lines)
