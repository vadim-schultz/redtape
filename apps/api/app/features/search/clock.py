"""The clock the search queues read, so tests can hold time still."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    """Return the current time in UTC."""
    return datetime.now(UTC)
