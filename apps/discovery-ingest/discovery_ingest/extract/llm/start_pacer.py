"""The Workers AI pacer: calls from every thread of one drain start at least one interval apart."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from types import TracebackType


class StartPacer:
    """Context manager: entering takes the next start slot under a lock and sleeps until it.

    Unlike :class:`~discovery_ingest.browser.throttle.Throttle`, which counts from the end of the previous call and so
    runs calls one at a time, this one counts from starts, so concurrent calls overlap while their starts stay spaced.
    """

    def __init__(
        self,
        min_interval_seconds: float,
        *,
        clock: Callable[[], float] | None = None,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        """Set the interval between starts; ``clock`` and ``sleep`` default to :func:`time.monotonic` and :func:`time.sleep`."""
        self._interval = min_interval_seconds
        self._clock = clock or time.monotonic
        self._sleep = sleep or time.sleep
        self._lock = threading.Lock()
        self._next_start = 0.0

    def __enter__(self) -> StartPacer:
        """Take the next start slot and wait until it."""
        with self._lock:
            start = max(self._clock(), self._next_start)
            self._next_start = start + self._interval
        if (wait := start - self._clock()) > 0:
            self._sleep(wait)
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, traceback: TracebackType | None
    ) -> None:
        """Nothing to release: the slot was taken on entry, so a call that fails leaves the next start spaced as usual."""
