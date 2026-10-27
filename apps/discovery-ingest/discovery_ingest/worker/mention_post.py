"""Post mentions to the machine API in chunks the route accepts."""

from __future__ import annotations

from collections.abc import Iterator, Sequence

from discovery_ingest.api_client import DiscoveryMachineClient
from discovery_ingest.mentions import MAX_MENTION_ITEMS, MentionItem


def _chunks(items: Sequence[MentionItem]) -> Iterator[Sequence[MentionItem]]:
    for start in range(0, len(items), MAX_MENTION_ITEMS):
        yield items[start : start + MAX_MENTION_ITEMS]


def post_mention_chunks(client: DiscoveryMachineClient, items: Sequence[MentionItem]) -> None:
    """Post ``items`` in batches of at most ``MAX_MENTION_ITEMS``; the first API error propagates."""
    for chunk in _chunks(items):
        client.post_mentions(chunk)
