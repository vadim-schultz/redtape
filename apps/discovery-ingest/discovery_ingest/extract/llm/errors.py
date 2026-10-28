"""What can go wrong with a Workers AI call, as the handler needs to tell it apart (error table of chapter E4)."""

from __future__ import annotations


class LlmError(Exception):
    """Base class for every Workers AI client failure."""


class LlmQuotaExceeded(LlmError):
    """The daily neuron allowance is used up: mark the day exhausted, release tasks and stop ``llm_quota``."""


class LlmAuthError(LlmError):
    """Cloudflare answered ``401`` or ``403``: the token or account is wrong; infrastructure, not the page."""


class LlmInvalidOutput(LlmError):
    """The model did not produce usable JSON (JSON mode not met or an unreadable body): one repair retry at most."""


class LlmRequestError(LlmError):
    """A failure of this one task: ``retryable`` for a 429 without the quota code, 5xx, timeout or connection error."""

    def __init__(self, message: str, *, retryable: bool) -> None:
        """Keep the ``retryable`` flag the task failure will carry."""
        super().__init__(message)
        self.retryable = retryable
