"""A configurable extractor for the extract framework tests."""

from __future__ import annotations

from collections.abc import Callable

from discovery_ingest.extract.base import PageContext
from discovery_ingest.mentions import MentionItem


class FakeExtractor:
    """Matches URLs containing ``host``; ``extract`` calls ``produce`` and records every page it was given."""

    def __init__(
        self,
        id: str = "fake",
        version: str = "1",
        *,
        host: str = "portal.example",
        produce: Callable[[str, PageContext], list[MentionItem]] | None = None,
    ) -> None:
        self.id = id
        self.version = version
        self._host = host
        self._produce = produce or (lambda html, ctx: [])
        self.pages: list[tuple[str, PageContext]] = []

    def matches(self, url: str, content_type: str | None) -> bool:
        """Match any URL on ``host``, whatever the content type."""
        return self._host in url

    def extract(self, html: str, ctx: PageContext) -> list[MentionItem]:
        """Record the page and return what ``produce`` makes of it."""
        self.pages.append((html, ctx))
        return self._produce(html, ctx)
