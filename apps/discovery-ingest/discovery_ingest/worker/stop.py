"""The signal a handler raises to end the drain: a limit or an infrastructure error, never a page problem."""

from __future__ import annotations

from discovery_ingest.schemas import StopReason


class StopDrain(Exception):
    """Release the in-flight and the unstarted tasks of the batch, then stop the drain with ``reason``."""

    def __init__(self, reason: StopReason, message: str = "") -> None:
        """Keep the stop ``reason`` and a human ``message`` for the report and the release call."""
        super().__init__(message or reason)
        self.reason: StopReason = reason
