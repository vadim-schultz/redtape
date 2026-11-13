"""Queue statistics shared by the leased queues: the age of the oldest ready task and the tasks finished in a day."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import ColumnElement, func
from sqlalchemy.orm import QueryableAttribute

RECENT_WINDOW = timedelta(hours=24)
"""How far back the completed and failed counts look."""


def oldest_ready(
    created_at: QueryableAttribute[datetime], ready: tuple[ColumnElement[bool], ...]
) -> ColumnElement[datetime]:
    """Return the earliest ``created_at`` among the ready rows, or NULL when none is ready."""
    return func.min(created_at).filter(*ready)


def finished_recently(
    finished: ColumnElement[bool], updated_at: QueryableAttribute[datetime], now: datetime
) -> ColumnElement[int]:
    """Return how many rows are ``finished`` and were last updated within the window before ``now``."""
    return func.count().filter(finished, updated_at >= now - RECENT_WINDOW)


def age_seconds(oldest: datetime | None, now: datetime) -> float | None:
    """Return the seconds from ``oldest`` to ``now``, or ``None`` when no row is ready."""
    return None if oldest is None else (now - oldest).total_seconds()
