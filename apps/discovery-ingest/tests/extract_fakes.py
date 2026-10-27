"""A configurable extractor for the extract framework tests."""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from typing import Any

import httpx
from discovery_ingest.extract.base import PageContext
from discovery_ingest.mentions import MentionItem

from render_fakes import FakeApi, task_json


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


ARTIFACT_ID = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
PAGE_URL = "https://portal.example/service/1"


def extract_task(
    *, artifact_id: uuid.UUID | None = ARTIFACT_ID, input_key: str | None = "fake@1", url: str = PAGE_URL
) -> dict[str, object]:
    """Return a claimed ``extract_page`` task as the claim route serves it."""
    return {**task_json(uuid.uuid4(), url, "extract_page"), "artifact_id": _text(artifact_id), "input_key": input_key}


def _text(value: uuid.UUID | None) -> str | None:
    return None if value is None else str(value)


class ExtractApi(FakeApi):
    """A machine API that also serves snapshot bytes and records posted mention batches."""

    def __init__(
        self, tasks: list[dict[str, object]], body: bytes = b"<p>x</p>", content_type: str = "text/html"
    ) -> None:
        super().__init__([tasks])
        self.body = body
        self.content_type = content_type
        self.content_status = 200
        self.mention_posts: list[list[dict[str, Any]]] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        """Answer the content and mentions routes, everything else as :class:`FakeApi`."""
        path = request.url.path
        if path.endswith("/content"):
            return self._content()
        if path.endswith("/candidates/mentions"):
            return self._mentions(request)
        return super().handler(request)

    def _content(self) -> httpx.Response:
        if self.content_status >= 400:
            return httpx.Response(self.content_status, text="content refused")
        return httpx.Response(200, content=self.body, headers={"content-type": self.content_type})

    def _mentions(self, request: httpx.Request) -> httpx.Response:
        items = json.loads(request.content)["items"]
        self.mention_posts.append(items)
        counts = {"candidates_created": len(items), "mentions_created": len(items), "mentions_updated": 0}
        return httpx.Response(200, json=counts)


def mention(ctx: PageContext, title: str = "Meldebescheinigung") -> MentionItem:
    """Return a valid required-document mention for the page ``ctx`` describes."""
    return MentionItem(
        catalogue_service_id=ctx.catalogue_service_id,
        title_i18n={"de": title},
        role="required",
        excerpt=title,
        source_field="page",
        extractor="fake",
        extractor_version="1",
    )
