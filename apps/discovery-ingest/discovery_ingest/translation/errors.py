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


class PermanentError(TranslationEngineError):
    """A failure of this batch that a retry will not fix."""


class UnusableOutputError(PermanentError):
    """The provider answered but not with one usable result per unit (short, malformed or off-schema)."""
