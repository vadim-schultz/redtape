"""Soft limit on database size: machine routes that create rows answer 507 above it."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass

import anyio
from litestar.connection import ASGIConnection
from litestar.exceptions import HTTPException
from litestar.handlers.base import BaseRouteHandler
from litestar.status_codes import HTTP_507_INSUFFICIENT_STORAGE
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.db import engine

logger = logging.getLogger(__name__)

SOFT_LIMIT_DETAIL = "database_soft_limit"
"""The 507 detail workers recognise: they stop with ``db_limit`` instead of failing the task."""
CACHE_SECONDS = 300.0


class DatabaseSoftLimitError(Exception):
    """The database is larger than ``db_soft_limit_bytes``."""


def read_database_size() -> int:
    """Return ``pg_database_size(current_database())`` in bytes."""
    with engine.connect() as connection:
        return int(connection.scalar(text("SELECT pg_database_size(current_database())")) or 0)


def configured_limit() -> int:
    """Return the soft limit currently configured."""
    return settings.db_soft_limit_bytes


@dataclass(slots=True)
class _CachedSize:
    bytes: int
    read_at: float


class DatabaseHeadroom:
    """Compare the database size, cached for five minutes, with the soft limit."""

    def __init__(
        self,
        read_size: Callable[[], int] = read_database_size,
        clock: Callable[[], float] = time.monotonic,
        limit: Callable[[], int] = configured_limit,
    ) -> None:
        """Inject the size query, a monotonic ``clock`` and the ``limit`` lookup."""
        self._read_size = read_size
        self._clock = clock
        self.limit = limit
        self._cached: _CachedSize | None = None

    def ensure_room(self) -> None:
        """Raise :class:`DatabaseSoftLimitError` above the limit; fail open when the size cannot be read."""
        size = self._size()
        if size is not None and size > self.limit():
            raise DatabaseSoftLimitError(SOFT_LIMIT_DETAIL)

    def _size(self) -> int | None:
        now = self._clock()
        if self._cached is not None and now - self._cached.read_at < CACHE_SECONDS:
            return self._cached.bytes
        return self._measure(now)

    def _measure(self, now: float) -> int | None:
        try:
            size = self._read_size()
        except SQLAlchemyError:
            logger.warning("could not read the database size; letting the write through", exc_info=True)
            return None
        self._cached = _CachedSize(size, now)
        return size


db_headroom = DatabaseHeadroom()


async def require_db_headroom(_: ASGIConnection, __: BaseRouteHandler) -> None:
    """Guard: answer 507 ``database_soft_limit`` while the database is above its soft limit."""
    try:
        await anyio.to_thread.run_sync(db_headroom.ensure_room)
    except DatabaseSoftLimitError as err:
        raise HTTPException(status_code=HTTP_507_INSUFFICIENT_STORAGE, detail=SOFT_LIMIT_DETAIL) from err


DB_WRITE_GUARDS = [require_db_headroom]
"""Attached to every machine route that creates rows; settle routes (complete, fail, release, claim) stay exempt."""
