"""Per-host minimum interval between requests."""

from __future__ import annotations

import time


class HostPacer:
    """Sleep as needed so requests to one host are at least ``min_interval_s`` apart."""

    def __init__(self, min_interval_s: float) -> None:
        self._min_interval_s = min_interval_s
        self._last_by_host: dict[str, float] = {}

    def wait(self, host: str) -> None:
        """Block until ``host`` may be requested again, then record the request time."""
        elapsed = time.monotonic() - self._last_by_host.get(host, 0.0)
        if elapsed < self._min_interval_s:
            time.sleep(self._min_interval_s - elapsed)
        self._last_by_host[host] = time.monotonic()
