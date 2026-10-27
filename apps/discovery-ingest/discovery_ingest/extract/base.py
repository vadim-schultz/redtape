"""The extractor interface and the page facts an extractor may rely on."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from discovery_ingest.mentions import MentionItem


@dataclass(frozen=True, slots=True)
class PageContext:
    """What is known about the snapshot being extracted; extractors make no network calls."""

    catalogue_service_id: UUID
    source_url: str
    final_url: str | None
    artifact_id: UUID


class Extractor(Protocol):
    """Hand-written rules for one host; dispatch is a registry lookup, never a branch in the worker."""

    id: str
    """Stable name such as ``verwaltung-bund``; the first half of the task's input key."""

    version: str
    """Bumped on any rule change; a new version enqueues a new task for the same snapshot."""

    def matches(self, url: str, content_type: str | None) -> bool:
        """Whether this extractor understands the page at ``url``."""
        ...

    def extract(self, html: str, ctx: PageContext) -> list[MentionItem]:
        """Return the mentions on the page; never raise on malformed markup."""
        ...
