"""Resumable search backfill (chapter 4)."""

from __future__ import annotations

from uuid import UUID

import pytest
from app.features.discovery.db_headroom import DatabaseSoftLimitError
from app.models.discovery import DiscoveryDocumentCandidate
from app.models.search import CandidateSearchText, EmbeddingTask
from scripts.backfill_search import (
    BackfillOptions,
    BackfillReport,
    StopReason,
    _parse_options,
    format_report,
    run_backfill,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from search_support import make_candidate, make_mention, search_service


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
    candidates = [make_candidate(session, title=f"Antrag {n}") for n in range(3)]
    make_mention(session, candidates[0], "Bitte Ausweis mitbringen", score=0.7)
    candidates.append(make_candidate(session, title=""))
    return sorted(candidates, key=lambda candidate: candidate.id)


def _count(session: Session, model: type) -> int:
    return int(session.scalar(select(func.count()).select_from(model)) or 0)


def _run(
    session: Session, headroom: OpenHeadroom | FullAfter, *, batch_size: int = 200, after: UUID | None = None
) -> BackfillReport:
    return run_backfill(session, BackfillOptions(after=after, batch_size=batch_size), headroom)


def test_backfill_writes_rows_and_tasks_for_all_candidates_and_is_idempotent(db_session: Session) -> None:
    _corpus(db_session)

    first = _run(db_session, OpenHeadroom())
    second = _run(db_session, OpenHeadroom())

    assert (first.totals.written, first.totals.unchanged, first.totals.skipped_empty, first.totals.enqueued) == (
        3,
        0,
        1,
        3,
    )
    assert (second.totals.written, second.totals.unchanged, second.totals.skipped_empty, second.totals.enqueued) == (
        0,
        3,
        1,
        0,
    )
    assert (_count(db_session, CandidateSearchText), _count(db_session, EmbeddingTask)) == (3, 3)
    assert first.stopped is second.stopped is StopReason.FINISHED


def test_backfill_reports_text_length_percentiles_of_the_rows(db_session: Session) -> None:
    _corpus(db_session)

    report = _run(db_session, OpenHeadroom())

    assert report.lengths.rows == 3
    assert 0 < report.lengths.p50 <= report.lengths.p95
    assert "p50" in format_report(report) and "written=3" in format_report(report)


def test_backfill_works_in_small_batches_and_resumes_after_an_id(db_session: Session) -> None:
    candidates = _corpus(db_session)

    report = _run(db_session, OpenHeadroom(), batch_size=1, after=candidates[1].id)

    assert report.processed == 2
    assert _count(db_session, CandidateSearchText) == sum(1 for row in candidates[2:] if row.title_i18n)
    assert report.last_id == candidates[3].id


def test_backfill_stops_cleanly_at_the_database_soft_limit_and_a_rerun_finishes(db_session: Session) -> None:
    candidates = _corpus(db_session)

    partial = _run(db_session, FullAfter(2), batch_size=1)
    resumed = _run(db_session, OpenHeadroom(), after=partial.last_id)

    assert partial.stopped is StopReason.DB_LIMIT
    assert partial.processed == 2 and partial.last_id == candidates[1].id
    assert "database_soft_limit" in format_report(partial) and str(partial.last_id) in format_report(partial)
    assert resumed.stopped is StopReason.FINISHED
    assert partial.processed + resumed.processed == len(candidates)


def test_backfill_uses_the_same_refresh_as_the_hooks(db_session: Session) -> None:
    candidate = make_candidate(db_session)
    search_service(db_session).refresh(candidate.id)

    report = _run(db_session, OpenHeadroom())

    assert (report.totals.written, report.totals.unchanged, report.totals.enqueued) == (0, 1, 0)


def test_options_are_parsed_from_the_command_line() -> None:
    options = _parse_options(["--after", "00000000-0000-0000-0000-000000000005", "--batch-size", "7"])

    assert (options.after, options.batch_size) == (UUID(int=5), 7)


def test_a_malformed_resume_id_is_rejected_before_anything_runs() -> None:
    with pytest.raises(SystemExit):
        _parse_options(["--after", "not-a-uuid"])
