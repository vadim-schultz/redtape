"""Post mentions to the machine API in chunks the route accepts."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from typing import TypeVar

from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.mentions import MAX_MENTION_ITEMS, MentionItem

T = TypeVar("T")


def chunked(items: Sequence[T], size: int) -> Iterator[Sequence[T]]:
    """Yield ``items`` in slices of at most ``size``."""
    for start in range(0, len(items), size):
        yield items[start : start + size]


def post_mention_chunks(client: DiscoveryIngestClient, items: Sequence[MentionItem]) -> int:
    """Post ``items`` in batches of at most ``MAX_MENTION_ITEMS``; return the codes the API dropped as unknown.

    The first API error propagates.
    """
    return sum(client.candidates.post_mentions(chunk).unknown_codes for chunk in chunked(items, MAX_MENTION_ITEMS))
