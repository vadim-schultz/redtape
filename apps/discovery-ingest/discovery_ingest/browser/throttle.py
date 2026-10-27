"""Minimum interval between any two Cloudflare calls in one process."""

from __future__ import annotations

import time
from collections.abc import Callable


class Throttle:
    """Sleep as needed so calls start at least ``min_interval_seconds`` apart; clock and sleep are injectable."""

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
        self._last: float | None = None

    def wait(self) -> None:
        """Block until a call may start, then record its start time."""
        if self._last is not None:
            remaining = self._last + self._interval - self._clock()
            if remaining > 0:
                self._sleep(remaining)
        self._last = self._clock()
