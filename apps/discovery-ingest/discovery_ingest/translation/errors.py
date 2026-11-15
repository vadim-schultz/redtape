"""The failure categories of the translation port; an adapter maps its provider's errors onto these and nothing else."""

from __future__ import annotations


class TranslationEngineError(Exception):
    """Base class of every failure an engine raises."""


class QuotaExceeded(TranslationEngineError):
    """The provider's allowance is used up: the drain releases its tasks and stops."""


class Unauthorised(TranslationEngineError):
    """The provider rejected the credentials: infrastructure, not the text; the drain stops."""


class TransientError(TranslationEngineError):
    """A timeout, a connection error, a throttle or a 5xx: the task may be retried later."""


class RateLimited(TransientError):
    """The provider throttled the call (HTTP 429): the drain releases its tasks without an attempt and stops.

    ``retry_after`` is the seconds the provider asked to wait, when it sent a ``Retry-After`` header; otherwise ``None``.
    """

    def __init__(self, message: str = "", *, retry_after: float | None = None) -> None:
        """Keep the message and the provider's wait in seconds, or ``None`` when it named none."""
        super().__init__(message)
        self.retry_after = retry_after


class PermanentError(TranslationEngineError):
    """A failure of this batch that a retry will not fix."""


class UnusableOutputError(PermanentError):
    """The provider answered but not with one usable result per unit (short, malformed or off-schema)."""
