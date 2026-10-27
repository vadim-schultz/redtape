"""The extractor registry: an ordered tuple, empty in production until chapter 18 adds the first extractor."""

from __future__ import annotations

from collections.abc import Sequence

from discovery_ingest.extract.base import Extractor

EXTRACTORS: tuple[Extractor, ...] = ()


def find_extractor(url: str, content_type: str | None, registry: Sequence[Extractor] = EXTRACTORS) -> Extractor | None:
    """Return the first extractor of ``registry`` that matches the page, or ``None`` when no extractor applies."""
    return next((extractor for extractor in registry if extractor.matches(url, content_type)), None)
