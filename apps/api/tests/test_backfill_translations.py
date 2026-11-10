"""Resumable translation backfill (chapter 14)."""

from __future__ import annotations

from uuid import UUID

from app.features.discovery.db_headroom import DatabaseSoftLimitError
from app.models.discovery import DiscoveryDocumentCandidate
from app.models.translation import TranslationTask
from scripts.backfill_translations import (
    BackfillOptions,
    BackfillReport,
    StopReason,
    _parse_options,
    format_report,
    run_backfill,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from search_support import make_candidate
from translation_support import human_row, stored_row, task_rows, unit_candidate, unit_hash


class OpenHeadroom:
    """Room for every write."""

    def ensure_room(self) -> None:
        """Never raise."""


class FullAfter:
    """Has room for ``batches`` checks, then reports the database at its limit."""

    def __init__(self, batches: int) -> None:
        self.left = batches

    def ensure_room(self) -> None:
        """Raise once the allowed batches are used up."""
        if self.left <= 0:
            raise DatabaseSoftLimitError("database_soft_limit")
        self.left -= 1


def _corpus(session: Session) -> list[DiscoveryDocumentCandidate]:
    """Four candidates: one translated and current, one stale, one fresh, one human-held; plus one without text."""
    current, stale, fresh, human = (unit_candidate(session, f"Antrag {n}", score=0.5) for n in range(4))
    stored_row(session, current, "en", unit_hash(session, current))
    stored_row(session, stale, "en", "old-hash")
    human_row(session, human, "en")
    make_candidate(session, title="")
    return sorted([current, stale, fresh, human], key=lambda candidate: candidate.id)


def _run(
    session: Session,
    headroom: OpenHeadroom | FullAfter | None = None,
    *,
    batch_size: int = 200,
    after: UUID | None = None,
    locale: str | None = "en",
) -> BackfillReport:
    options = BackfillOptions(after=after, batch_size=batch_size, locale=locale)
    return run_backfill(session, options, headroom or OpenHeadroom())


def _count(session: Session) -> int:
    return int(session.scalar(select(func.count()).select_from(TranslationTask)) or 0)


def test_backfill_enqueues_only_missing_and_stale_translations_and_is_idempotent(db_session: Session) -> None:
    _corpus(db_session)

    first = _run(db_session)
    second = _run(db_session)

    assert (first.totals.enqueued, first.totals.missing, first.totals.stale) == (2, 1, 1)
    assert (first.totals.up_to_date, first.totals.human_protected, first.totals.no_source) == (1, 1, 1)
    assert (second.totals.enqueued, second.totals.stale, second.totals.up_to_date) == (0, 1, 1)
    assert _count(db_session) == 2
    assert all(task.locale == "en" for task in task_rows(db_session))


def test_backfill_of_one_locale_leaves_the_others_alone(db_session: Session) -> None:
    unit_candidate(db_session)

    _run(db_session, locale="tr")

    assert {task.locale for task in task_rows(db_session)} == {"tr"}


def test_backfill_without_a_locale_covers_every_target_locale(db_session: Session) -> None:
    from app.config import settings

    unit_candidate(db_session)

    _run(db_session, locale=None)

    assert {task.locale for task in task_rows(db_session)} == set(settings.translation_target_locale_codes)


def test_backfill_resumes_after_the_given_id_and_commits_by_batch(db_session: Session) -> None:
    ordered = sorted((unit_candidate(db_session, f"Antrag {n}") for n in range(4)), key=lambda c: c.id)

    resumed = _run(db_session, after=ordered[1].id, batch_size=1)

    assert (resumed.processed, resumed.last_id) == (2, ordered[-1].id)
    assert {task.candidate_id for task in task_rows(db_session)} == {ordered[2].id, ordered[3].id}


def test_backfill_stops_cleanly_at_the_database_soft_limit_and_reports_where_to_resume(db_session: Session) -> None:
    for n in range(3):
        unit_candidate(db_session, f"Antrag {n}")

    report = _run(db_session, FullAfter(1), batch_size=1)

    assert (report.processed, report.stopped) == (1, StopReason.DB_LIMIT)
    assert f"--after {report.last_id}" in format_report(report)
    assert _count(db_session) == 1


def test_the_report_names_the_counts_and_the_options_parse() -> None:
    report = BackfillReport()

    options = _parse_options(["--after", "11111111-2222-3333-4444-555555555555", "--locale", "tr", "--batch-size", "5"])

    assert (options.locale, options.batch_size, str(options.after)) == ("tr", 5, "11111111-2222-3333-4444-555555555555")
    assert "enqueued=0" in format_report(report) and "up_to_date=0" in format_report(report)
