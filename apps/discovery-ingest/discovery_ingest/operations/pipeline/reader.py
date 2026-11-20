"""Read the plan's facts from the machine API, once per read: the queue summaries, the ledger and the sweep candidates."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date

from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.operations.pipeline.deadline import days_left
from discovery_ingest.operations.pipeline.plan import PlanFacts
from discovery_ingest.schemas import DiscoveryTaskKind

TASK_GROUPS: Mapping[str, tuple[DiscoveryTaskKind, ...]] = {
    "seed": ("fetch_url", "enrich_metadata", "harvest_payload"),
    "extract_page": ("extract_page",),
    "render": ("render_page",),
    "llm": ("llm_extract",),
    "capture": ("capture_screenshot",),
}
"""The stages that read a task queue, and the kinds each one claims."""
SWEEP_PAGE_LIMIT = 50
"""Most pages without a screenshot the plan counts; the sweeper takes at most this many on one run."""


@dataclass(frozen=True, slots=True)
class PlanContext:
    """The settings the reader needs: the day, the embedding model, the neuron reserve, the tail and the model."""

    today: date
    embedding_model: str
    query_embed_reserve: float
    tail_locales: tuple[str, ...]
    llm_model: str


def read_plan_facts(client: DiscoveryIngestClient, context: PlanContext) -> PlanFacts:
    """Read every summary and the ledger once, and return the facts the planner works from."""
    remaining = _remaining(client)
    unconfigured = {*(() if context.llm_model else ("llm",)), *(() if context.tail_locales else ("card_tail",))}
    return PlanFacts(
        ready={**_task_ready(client), **_queue_ready(client, context)},
        headroom={
            "browser_seconds": remaining.get("browser_seconds", 0.0),
            "neurons": max(remaining.get("neurons", 0.0) - context.query_embed_reserve, 0.0),
        },
        actions_minutes_remaining=remaining.get("actions_minutes", 0.0),
        days_left=days_left(context.today),
        unconfigured=frozenset(unconfigured),
    )


def _remaining(client: DiscoveryIngestClient) -> dict[str, float]:
    """Return what is left of each ledger resource in its current period; an exhausted row has nothing left."""
    snapshot = client.budget.snapshot()
    return {row.resource: 0.0 if row.exhausted else row.remaining for row in snapshot.items}


def _task_ready(client: DiscoveryIngestClient) -> dict[str, int]:
    """Return the ready work of each task-queue stage; capture also counts the pages a sweep would shoot."""
    ready = {stage: client.tasks.summary(kinds=kinds).pending_ready for stage, kinds in TASK_GROUPS.items()}
    ready["capture"] += _uncaptured_pages(client)
    return ready


def _uncaptured_pages(client: DiscoveryIngestClient) -> int:
    """Return how many rendered pages have no screenshot, up to the sweep's page limit."""
    page = client.artifacts.missing_screenshot(limit=SWEEP_PAGE_LIMIT)
    return min(len(page.items), SWEEP_PAGE_LIMIT)


def _queue_ready(client: DiscoveryIngestClient, context: PlanContext) -> dict[str, int]:
    """Return the ready work of the embedding, card and page queues; the tail counts the tail locales only."""
    cards = client.translations.summary()
    tail = sum(row.pending_ready for row in cards.locales if row.locale in context.tail_locales)
    return {
        "embed": client.embeddings.summary(context.embedding_model).pending_ready,
        "card_translation": cards.pending_ready,
        "card_tail": tail,
        "page_translation": client.snapshots.summary().pending_ready,
    }
