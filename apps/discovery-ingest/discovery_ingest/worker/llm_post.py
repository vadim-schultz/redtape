"""Post what the model found: mentions first so the edge endpoints exist, both in chunks the routes accept."""

from __future__ import annotations

from collections.abc import Sequence

from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.edges import MAX_EDGE_ITEMS, EdgeItem
from discovery_ingest.mentions import MentionItem
from discovery_ingest.worker.mention_post import chunked, post_mention_chunks


def post_staged(client: DiscoveryIngestClient, mentions: Sequence[MentionItem], edges: Sequence[EdgeItem]) -> int:
    """Post ``mentions`` and then ``edges``; return the codes the API dropped as unknown. The first API error propagates."""
    unknown_codes = post_mention_chunks(client, mentions)
    for chunk in chunked(edges, MAX_EDGE_ITEMS):
        client.candidates.post_edges(chunk)
    return unknown_codes
