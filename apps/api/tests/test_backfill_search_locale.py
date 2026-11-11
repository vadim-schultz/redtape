"""Resumable search backfill of translated locales (chapter 16)."""

from __future__ import annotations

from uuid import UUID

import pytest
from app.features.discovery.db_headroom import DatabaseSoftLimitError
from app.models.discovery import DiscoveryDocumentCandidate
from app.shared.object_store import InMemoryObjectStore, ObjectStoreQuotaError
from scripts.backfill_search import _parse_options
from scripts.backfill_search_locale import (
    LocaleBackfillOptions,
    LocaleBackfillReport,
    StopReason,
    format_locale_report,
    run_locale_backfill,
)
from sqlalchemy.orm import Session

from search_locale_support import embedding_tasks, keyword_hits, payload, search_text_row, store_translation
from translation_support import unit_candidate


class OpenHeadroom:
    """Room for every write."""

    def ensure_room(self) -> None:
        """Never raise."""


class FullHeadroom:
    """The database is at its soft limit."""

    def ensure_room(self) -> None:
        """Always raise."""
        raise DatabaseSoftLimitError("database_soft_limit")


class QuotaStore(InMemoryObjectStore):
    """A store whose reads hit the monthly cap."""

    def get(self, key: str) -> bytes:
        raise ObjectStoreQuotaError("Monthly r2_class_b budget is exhausted")


def _corpus(session: Session, backend: InMemoryObjectStore, count: int = 3) -> list[DiscoveryDocumentCandidate]:
    candidates = [unit_candidate(session, f"Antrag {n}") for n in range(count)]
    for candidate in candidates:
        store_translation(session, backend, candidate, payload("tr", f"Başvuru {candidate.id.hex[:6]}", "Kimlikler"))
    return sorted(candidates, key=lambda candidate: candidate.id)


def _run(
    session: Session,
    backend: InMemoryObjectStore,
    headroom: OpenHeadroom | FullHeadroom | None = None,
    *,
    batch_size: int = 200,
    after: UUID | None = None,
) -> LocaleBackfillReport:
    options = LocaleBackfillOptions("tr", after=after, batch_size=batch_size)
    return run_locale_backfill(session, backend, options, headroom or OpenHeadroom())


def test_backfill_builds_rows_from_existing_translation_objects_and_is_idempotent(db_session: Session) -> None:
    backend = InMemoryObjectStore()
    candidates = _corpus(db_session, backend)

    first = _run(db_session, backend, batch_size=2)
    second = _run(db_session, backend)

    assert (first.processed, first.totals.written, first.totals.enqueued) == (3, 3, 3)
    assert (second.processed, second.totals.written, second.totals.unchanged, second.totals.enqueued) == (3, 0, 3, 0)
    assert all(search_text_row(db_session, candidate, "tr") for candidate in candidates)
    assert sorted(keyword_hits(db_session, "kimlik", "tr")) == [candidate.id for candidate in candidates]
    assert len(embedding_tasks(db_session, "tr")) == 3
    assert "written=3" in format_locale_report(first)


def test_an_index_row_whose_object_is_missing_is_reported_and_skipped_while_others_process(
    db_session: Session,
) -> None:
    backend = InMemoryObjectStore()
    candidates = _corpus(db_session, backend)
    lost = store_translation(db_session, backend, unit_candidate(db_session, "Verloren"), payload("tr", "Kayıp"))
    backend.delete(lost.key)

    report = _run(db_session, backend)

    assert (report.processed, report.totals.written, report.totals.object_unreadable) == (4, 3, 1)
    assert len(report.unreadable) == 1
    assert all(search_text_row(db_session, candidate, "tr") for candidate in candidates)
    assert str(report.unreadable[0]) in format_locale_report(report)


def test_the_backfill_stops_cleanly_when_the_object_store_refuses_reads(db_session: Session) -> None:
    backend = InMemoryObjectStore()
    _corpus(db_session, backend)

    report = _run(db_session, QuotaStore())

    assert (report.stopped, report.totals.written) == (StopReason.STORE_UNAVAILABLE, 0)


def test_the_backfill_stops_when_the_database_is_at_its_soft_limit(db_session: Session) -> None:
    backend = InMemoryObjectStore()
    _corpus(db_session, backend)

    report = _run(db_session, backend, FullHeadroom())

    assert (report.stopped, report.processed) == (StopReason.DB_LIMIT, 0)


def test_locale_is_repeatable_and_limited_to_the_translation_targets() -> None:
    assert _parse_options(["--locale", "tr", "--locale", "ru"]).locales == ("tr", "ru")
    assert _parse_options([]).locales == ()
    with pytest.raises(SystemExit):
        _parse_options(["--locale", "de"])
