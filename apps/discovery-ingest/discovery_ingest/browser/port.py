"""The browser port: what the worker needs from a rendering service, nothing about HTTP."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class RenderedPage:
    """A rendered DOM with its browser cost and what the browser saw (``None`` when the service did not say)."""

    html: str
    ms_used: int
    http_status: int | None = None
    final_url: str | None = None


@dataclass(frozen=True, slots=True)
class ScreenshotImage:
    """A full-page image; ``html``, ``http_status`` and ``final_url`` describe the same session when the service said."""

    data: bytes
    content_type: str
    ms_used: int
    html: str | None = None
    http_status: int | None = None
    final_url: str | None = None


class BrowserClient(Protocol):
    """Render a URL, or capture it as an image; every call may raise a :class:`BrowserError`."""

    def render(self, url: str) -> RenderedPage:
        """Return the rendered DOM of ``url``."""
        ...

    def screenshot(self, url: str) -> ScreenshotImage:
        """Return a full-page image of ``url`` (and its DOM when available)."""
        ...
