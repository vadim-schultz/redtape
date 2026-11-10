"""What the candidate backfills share: the database headroom check and the reason a run stopped."""

from __future__ import annotations

import enum
from typing import Protocol

from app.features.discovery.db_headroom import SOFT_LIMIT_DETAIL, DatabaseSoftLimitError

DEFAULT_BATCH_SIZE = 200


class Headroom(Protocol):
    """Whatever can say the database has room for more writes."""

    def ensure_room(self) -> None:
        """Raise :class:`DatabaseSoftLimitError` when the database is at its soft limit."""


class StopReason(enum.StrEnum):
    """Why a run ended."""

    FINISHED = "finished"
    DB_LIMIT = SOFT_LIMIT_DETAIL


def room_stop(headroom: Headroom) -> StopReason | None:
    """Return :attr:`StopReason.DB_LIMIT` when the database is at its soft limit, ``None`` when there is room."""
    try:
        headroom.ensure_room()
    except DatabaseSoftLimitError:
        return StopReason.DB_LIMIT
    return None
