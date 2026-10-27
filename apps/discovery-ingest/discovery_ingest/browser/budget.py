"""The browser time one drain may spend, summed from the milliseconds each call reports."""

from __future__ import annotations


class BrowserBudget:
    """Accumulate browser milliseconds against a limit in seconds."""

    def __init__(self, limit_seconds: float) -> None:
        """Set the limit; it must be positive."""
        if limit_seconds <= 0:
            raise ValueError("browser budget limit must be positive")
        self._limit_ms = limit_seconds * 1000
        self._used_ms = 0

    def spend(self, ms_used: int) -> None:
        """Add the cost of one call."""
        if ms_used < 0:
            raise ValueError("browser time spent must be non-negative")
        self._used_ms += ms_used

    @property
    def used_seconds(self) -> float:
        """Browser seconds spent so far."""
        return self._used_ms / 1000

    @property
    def exhausted(self) -> bool:
        """Whether the limit is reached."""
        return self._used_ms >= self._limit_ms
