"""What can go wrong with a Cloudflare call, as the worker needs to tell it apart."""

from __future__ import annotations


class BrowserError(Exception):
    """Base class for every browser client failure."""


class BrowserQuotaExceeded(BrowserError):
    """Cloudflare answered ``429``: stop the run and release tasks; ``retry_after`` is in seconds when sent."""

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        """Keep the optional ``Retry-After`` value."""
        super().__init__(message)
        self.retry_after = retry_after


class BrowserAuthError(BrowserError):
    """Cloudflare answered ``401`` or ``403``: the token or account is wrong; this is infrastructure, not the page."""


class BrowserRequestError(BrowserError):
    """A failure of this one task: ``retryable`` for a 5xx, timeout or connection error, permanent otherwise."""

    def __init__(self, message: str, *, retryable: bool) -> None:
        """Keep the ``retryable`` flag the task failure will carry."""
        super().__init__(message)
        self.retryable = retryable


class ScreenshotOversize(BrowserError):
    """The image is larger than the screenshot cap; the caller completes the task with ``oversize``."""

    def __init__(self, byte_size: int) -> None:
        """Keep the size that broke the cap."""
        super().__init__(f"screenshot is {byte_size} bytes")
        self.byte_size = byte_size
