"""Result of one polite GET attempt and the abort that stands for a failed one."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FetchOutcome:
    """Result of one polite GET attempt."""

    http_status: int | None
    content_type: str | None
    byte_length: int | None
    error_message: str | None
    body: bytes | None = None
    final_url: str | None = None
    redirect_count: int = 0


def failure_outcome(message: str, *, http_status: int | None = None) -> FetchOutcome:
    """Build the outcome of a fetch that failed with ``message``."""
    return FetchOutcome(
        http_status=http_status,
        content_type=None,
        byte_length=None,
        error_message=message,
        body=None,
    )


class FetchAbort(Exception):
    """A fetch that must stop with a failure outcome."""

    def __init__(self, message: str, *, http_status: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.http_status = http_status

    def outcome(self) -> FetchOutcome:
        """Return the failure outcome this abort stands for."""
        return failure_outcome(self.message, http_status=self.http_status)
