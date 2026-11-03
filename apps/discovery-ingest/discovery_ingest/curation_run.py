"""Post a curation plan through the machine routes and total what the API answered (chapter 11)."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from typing import TypeVar

from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.curation_plan import CurationPlan
from discovery_ingest.edges import MAX_EDGE_ITEMS, EdgeItem
from discovery_ingest.mentions import MAX_MENTION_ITEMS

_T = TypeVar("_T")


def batches(items: Sequence[_T], size: int) -> Iterator[Sequence[_T]]:
    """Yield consecutive slices of ``items`` of at most ``size``; ``size`` below one is a ``ValueError``."""
    if size < 1:
        raise ValueError(f"batch size must be at least 1; got {size}")
    for start in range(0, len(items), size):
        yield items[start : start + size]


@dataclass(slots=True)
class Totals:
    """What a run created, updated or skipped, with the reason line of each skipped edge."""

    mentions_created: int = 0
    mentions_updated: int = 0
    edges_created: int = 0
    edges_updated: int = 0
    edges_skipped: int = 0
    unknown_codes: int = 0
    skipped: list[str] = field(default_factory=list)

    @property
    def refused(self) -> bool:
        """Whether the API skipped an edge or dropped a code, which makes the run fail."""
        return bool(self.edges_skipped or self.unknown_codes)


def _post_mentions(client: DiscoveryIngestClient, plan: CurationPlan, totals: Totals) -> None:
    for batch in batches(plan.mentions, MAX_MENTION_ITEMS):
        answer = client.candidates.post_mentions(batch)
        totals.mentions_created += answer.mentions_created
        totals.mentions_updated += answer.mentions_updated
        totals.unknown_codes += answer.unknown_codes


def _skip_line(edge: EdgeItem, reason: str) -> str:
    return f"{edge.parent_title_i18n['de']!r} requires {edge.required_title_i18n['de']!r}: {reason}"


def _post_edges(client: DiscoveryIngestClient, plan: CurationPlan, totals: Totals) -> None:
    for start, batch in zip(
        range(0, len(plan.edges), MAX_EDGE_ITEMS), batches(plan.edges, MAX_EDGE_ITEMS), strict=True
    ):
        answer = client.candidates.post_edges(batch)
        totals.edges_created += answer.edges_created
        totals.edges_updated += answer.edges_updated
        totals.edges_skipped += answer.edges_skipped
        totals.skipped += [_skip_line(plan.edges[start + s.index], s.reason) for s in answer.skipped]


def post_plan(client: DiscoveryIngestClient, plan: CurationPlan) -> Totals:
    """Post the mentions, then the edges (both ends must exist first), in batches of at most 100."""
    totals = Totals()
    _post_mentions(client, plan, totals)
    _post_edges(client, plan, totals)
    return totals
