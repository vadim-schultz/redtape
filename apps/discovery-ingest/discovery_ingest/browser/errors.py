"""What can go wrong with a Cloudflare call, as the worker needs to tell it apart."""

from __future__ import annotations

from discovery_ingest.browser.port import RenderedPage


class BrowserError(Exception):
    """Base class for every browser client failure; ``ms_used`` is the browser time the failed call cost, when known."""

    def __init__(self, message: str = "", *, ms_used: int | None = None) -> None:
        """Keep the message and the browser milliseconds the call cost (``None`` when unknown)."""
        super().__init__(message)
        self.ms_used = ms_used


class BrowserQuotaExceeded(BrowserError):
    """Cloudflare answered ``429``: stop the run and release tasks; ``retry_after`` is in seconds when sent."""

    def __init__(self, message: str, retry_after: float | None = None, *, ms_used: int | None = None) -> None:
        """Keep the optional ``Retry-After`` value."""
        super().__init__(message, ms_used=ms_used)
        self.retry_after = retry_after


class BrowserAuthError(BrowserError):
    """Cloudflare answered ``401`` or ``403``: the token or account is wrong; this is infrastructure, not the page."""


class BrowserRequestError(BrowserError):
    """A failure of this one task: ``retryable`` for a 5xx, timeout or connection error, permanent otherwise."""

    def __init__(self, message: str, *, retryable: bool, ms_used: int | None = None) -> None:
        """Keep the ``retryable`` flag the task failure will carry."""
        super().__init__(message, ms_used=ms_used)
        self.retryable = retryable


class ScreenshotUnreadable(BrowserRequestError):
    """The fused call returned no image that reads as one; a permanent request error whose DOM is kept when Cloudflare sent one."""

    page: RenderedPage | None

    def __init__(self, message: str, *, ms_used: int, page: RenderedPage | None = None) -> None:
        """Keep the message, the browser milliseconds the call cost and the DOM of that call."""
        super().__init__(message, retryable=False, ms_used=ms_used)
        self.page = page


class ScreenshotOversize(BrowserError):
    """The image is larger than the screenshot cap; the caller completes the task with ``oversize``."""

    ms_used: int
    """Always known: the oversize image is returned as a value, and its browser time is booked like any other call."""
    page: RenderedPage | None
    """The DOM of the same call when Cloudflare sent one: the fused render keeps it when the image is too large."""

    def __init__(self, byte_size: int, ms_used: int = 0, *, page: RenderedPage | None = None) -> None:
        """Keep the size that broke the cap, the browser milliseconds the call cost and the DOM of that call."""
        super().__init__(f"screenshot is {byte_size} bytes", ms_used=ms_used)
        self.byte_size = byte_size
        self.page = page
