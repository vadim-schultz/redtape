"""The operator sweep that queues Azure upgrades for tail rows: bounded, idle-gated and stopped by the database limit (chapter 7)."""

from __future__ import annotations

from app.features.discovery.db_headroom import DatabaseSoftLimitError
from app.models.search import WorkTaskStatus
from scripts.upgrade_tail_translations import StopReason, run_upgrade
from sqlalchemy.orm import Session

from translation_support import stored_row, task_rows, unit_candidate, unit_hash


class OpenHeadroom:
    """Room for every write."""

    def ensure_room(self) -> None:
        """Never raise."""


class FullHeadroom:
    """The database is at its soft limit."""

    def ensure_room(self) -> None:
        """Raise the soft-limit error every time."""
        raise DatabaseSoftLimitError("database_soft_limit")


def _tail_row(session: Session, title: str) -> None:
    candidate = unit_candidate(session, title)
    stored_row(session, candidate, "tr", unit_hash(session, candidate))


def test_the_sweep_queues_the_tail_rows_and_reports_how_many(db_session: Session) -> None:
    _tail_row(db_session, "Antrag Sweep Eins")
    _tail_row(db_session, "Antrag Sweep Zwei")

    report = run_upgrade(db_session, limit=5, headroom=OpenHeadroom())

    assert (report.queued, report.stopped) == (2, StopReason.FINISHED)
    assert len(task_rows(db_session, WorkTaskStatus.PENDING)) == 2


def test_the_sweep_queues_nothing_at_the_database_soft_limit(db_session: Session) -> None:
    _tail_row(db_session, "Antrag Sweep Voll")

    report = run_upgrade(db_session, limit=5, headroom=FullHeadroom())

    assert (report.queued, report.stopped) == (0, StopReason.DB_LIMIT)
    assert task_rows(db_session) == []
