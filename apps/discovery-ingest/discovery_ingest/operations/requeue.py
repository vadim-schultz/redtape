"""``llm requeue`` and ``capture requeue``: queue one task per page and count the answers."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from itertools import islice
from uuid import UUID

import httpx
from pydantic import ValidationError

from discovery_ingest.artifacts import ArtifactRead
from discovery_ingest.candidate_sources import CandidateSourceRead, SourceQuery
from discovery_ingest.client import DiscoveryIngestClient, DiscoveryMachineApiError
from discovery_ingest.latest_snapshots import latest_snapshots
from discovery_ingest.schemas import TaskEnqueueRequest
from discovery_ingest.worker.capture_enqueue import capture_request
from discovery_ingest.worker.llm_enqueue import llm_extract_request

DEFAULT_LIMIT = 50
MAX_LIMIT = 200
"""More pages than this in one run would commit more neurons or browser seconds than a day allows; refused before any call."""
PAGE_SIZE = 100
"""The most the sources route serves in one page."""
MAX_SERVICE_IDS = 20
"""The most procedures one run may name; the route refuses more."""


@dataclass(slots=True)
class Counts:
    """What a requeue did, one count per page: queued now, already queued under this key, or refused."""

    pages: int = 0
    queued: int = 0
    already_queued: int = 0
    failed: int = 0


def enqueue_counted(client: DiscoveryIngestClient, request: TaskEnqueueRequest, counts: Counts) -> None:
    """Enqueue ``request`` and count the answer; the queue's identity answers ``created`` false for a known key."""
    try:
        created = client.tasks.enqueue(request).created
    except (DiscoveryMachineApiError, httpx.HTTPError, ValidationError):
        counts.failed += 1
        return
    counts.queued += created
    counts.already_queued += not created


def llm_requeue(client: DiscoveryIngestClient, *, host: str | None, limit: int, model: str, dry_run: bool) -> Counts:
    """Queue ``llm_extract`` for the latest snapshot of each catalogue row, or only count them when ``dry_run``."""
    snapshots = latest_snapshots(client, host, limit)
    if dry_run:
        return Counts(pages=len(snapshots))
    return _enqueue_llm(client, snapshots, model)


def _enqueue_llm(client: DiscoveryIngestClient, snapshots: list[ArtifactRead], model: str) -> Counts:
    counts = Counts(pages=len(snapshots))
    for artifact in snapshots:
        enqueue_counted(client, llm_extract_request(artifact, model), counts)
    return counts


def _sources(
    client: DiscoveryIngestClient, host: str | None, service_ids: Sequence[UUID], limit: int
) -> Iterator[CandidateSourceRead]:
    """Yield the pages without a screenshot, busiest first, one route page at a time."""
    offset = 0
    while True:
        page = client.candidates.list_sources(
            SourceQuery(
                host=host,
                missing="screenshot",
                candidate_id=None,
                service_ids=list(service_ids),
                offset=offset,
                limit=min(PAGE_SIZE, limit - offset),
            )
        )
        yield from page.items
        offset += len(page.items)
        if not page.items or offset >= min(page.total, limit):
            return


def capture_requeue(
    client: DiscoveryIngestClient,
    *,
    host: str | None,
    limit: int,
    service_ids: Sequence[UUID],
    dry_run: bool,
) -> Counts:
    """Queue ``capture_screenshot`` for each page without one, or only count them when ``dry_run``."""
    sources = list(islice(_sources(client, host, service_ids, limit), limit))
    if dry_run:
        return Counts(pages=len(sources))
    counts = Counts(pages=len(sources))
    for source in sources:
        enqueue_counted(client, capture_request(source.catalogue_service_id, source.source_url), counts)
    return counts
