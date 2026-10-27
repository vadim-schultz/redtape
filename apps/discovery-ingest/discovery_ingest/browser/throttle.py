"""Minimum interval between any two Cloudflare calls in one process, counted from the end of the previous call."""

from __future__ import annotations

import time
from collections.abc import Callable
from types import TracebackType


class Throttle:
    """Context manager: entering waits until the interval since the last call ended has passed.

    The probe saw a ``429`` (``Rate limit exceeded``, ``Retry-After: 10``) for a call that started 11 s after the
    start of a slow one, so the interval runs from the end of a call, not from its start.
    """

    def __init__(
        self,
        min_interval_seconds: float,
        *,
        clock: Callable[[], float] | None = None,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        """Set the interval; ``clock`` and ``sleep`` default to :func:`time.monotonic` and :func:`time.sleep`."""
        self._interval = min_interval_seconds
        self._clock = clock or time.monotonic
        self._sleep = sleep or time.sleep
        self._ready_at: float | None = None

    def __enter__(self) -> Throttle:
        """Block until a call may start."""
        if self._ready_at is not None and (remaining := self._ready_at - self._clock()) > 0:
            self._sleep(remaining)
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, traceback: TracebackType | None
    ) -> None:
        """Start the interval; an error inside the call does not skip it."""
        self._ready_at = self._clock() + self._interval
