"""Result of one polite GET attempt, its failure kinds, and the abort that stands for a failed one."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum


class FetchFailure(StrEnum):
    """Why a fetch failed without a usable HTTP response."""

    TIMEOUT = "timeout"
    CONNECTION = "connection"
    ROBOTS_UNAVAILABLE = "robots_unavailable"
    ROBOTS_DISALLOWED = "robots_disallowed"
    BLOCKED = "blocked"
    TOO_LARGE = "too_large"
    REDIRECT = "redirect"


_RETRYABLE_FAILURES = frozenset({FetchFailure.TIMEOUT, FetchFailure.CONNECTION, FetchFailure.ROBOTS_UNAVAILABLE})


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
    retryable: bool = False
    failure: FetchFailure | None = None

    @property
    def failed(self) -> bool:
        """Whether the attempt did not end in a 2xx response."""
        status = self.http_status
        return self.error_message is not None or status is None or not 200 <= status < 300

    @property
    def failure_message(self) -> str:
        """Human-readable reason for a failed attempt."""
        return self.error_message or f"HTTP {self.http_status}"


def classify(outcome: FetchOutcome) -> bool:
    """Return whether a later attempt could succeed: timeout, reset, 429 and 5xx are retryable."""
    if outcome.failure is not None:
        return outcome.failure in _RETRYABLE_FAILURES
    status = outcome.http_status
    return status is not None and (status == 429 or status >= 500)


def classified(outcome: FetchOutcome) -> FetchOutcome:
    """Return ``outcome`` with its ``retryable`` flag set by :func:`classify`."""
    return replace(outcome, retryable=classify(outcome))


def failure_outcome(message: str, failure: FetchFailure, *, http_status: int | None = None) -> FetchOutcome:
    """Build the outcome of a fetch that failed with ``message``."""
    return FetchOutcome(
        http_status=http_status,
        content_type=None,
        byte_length=None,
        error_message=message,
        body=None,
        failure=failure,
    )


class FetchAbort(Exception):
    """A fetch that must stop with a failure outcome."""

    def __init__(self, message: str, failure: FetchFailure, *, http_status: int | None = None) -> None:
        """Bind the message, the failure category and the optional HTTP status the outcome reports."""
        super().__init__(message)
        self.message = message
        self.failure = failure
        self.http_status = http_status

    def outcome(self) -> FetchOutcome:
        """Return the failure outcome this abort stands for."""
        return failure_outcome(self.message, self.failure, http_status=self.http_status)
