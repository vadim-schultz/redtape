"""Queue capture_screenshot tasks: a sweeper over rendered pages with no screenshot, and the post-extraction hook (chapter 8)."""

from __future__ import annotations

import sys
from uuid import UUID

import httpx
from pydantic import ValidationError

from discovery_ingest.artifacts import ArtifactRead
from discovery_ingest.client import DiscoveryIngestClient, DiscoveryMachineApiError
from discovery_ingest.schemas import ClaimedTask, TaskEnqueueRequest

CAPTURE_PRIORITY = 300
"""Claimed after renders (100) and extractions, because the queue takes lower numbers first."""
CAPTURE_INPUT_KEY = "shot@1"
"""The same for every extractor and version, so one page keeps one capture however often it is extracted."""
ENQUEUE_ERRORS = (DiscoveryMachineApiError, httpx.HTTPError, ValidationError)


def capture_request(catalogue_service_id: UUID, target_url: str) -> TaskEnqueueRequest:
    """Return the ``capture_screenshot`` enqueue request for the page ``target_url`` of one catalogue row."""
    return TaskEnqueueRequest(
        catalogue_service_id=catalogue_service_id,
        kind="capture_screenshot",
        target_url=target_url,
        priority=CAPTURE_PRIORITY,
        input_key=CAPTURE_INPUT_KEY,
    )


def sweep_screenshots(client: DiscoveryIngestClient, *, limit: int) -> int:
    """Queue ``capture_screenshot`` for up to ``limit`` rendered pages with no screenshot; return how many were newly queued.

    The pages come from stored state (the newest HTML snapshot of each rendered row without a screenshot), so the
    sweep does not depend on an LLM task completing. A refused read or enqueue is logged and never raised.
    """
    try:
        gaps = client.artifacts.missing_screenshot(limit=limit).items
    except (DiscoveryMachineApiError, httpx.HTTPError) as err:
        print(f"screenshot sweep read failed: {err}", file=sys.stderr)
        return 0
    return sum(_queue_gap(client, gap) for gap in gaps)


def _queue_gap(client: DiscoveryIngestClient, gap: ArtifactRead) -> int:
    """Return 1 when the capture was newly queued, else 0 (already queued, or refused and logged)."""
    try:
        created = client.tasks.enqueue(capture_request(gap.catalogue_service_id, gap.source_url)).created
    except ENQUEUE_ERRORS as err:
        print(f"capture enqueue failed for {gap.source_url}: {err}", file=sys.stderr)
        return 0
    return int(created)


def enqueue_screenshot_for_mentions(client: DiscoveryIngestClient, task: ClaimedTask) -> bool:
    """Enqueue ``capture_screenshot`` for the page ``task`` extracted; return false when it failed (logged, never raised).

    Call it after at least one mention was posted, from any extractor handler. The page is ``task.target_url``, the
    artifact's ``source_url``, which already is the redirect-resolved URL of the plain fetch. A page that already has
    a screenshot is a no-op that still reports success.
    """
    try:
        if not _awaits_screenshot(client, task):
            return True
        client.tasks.enqueue(capture_request(task.catalogue_service_id, task.target_url))
    except ENQUEUE_ERRORS as err:
        print(f"capture enqueue failed for {task.target_url}: {err}", file=sys.stderr)
        return False
    return True


def _awaits_screenshot(client: DiscoveryIngestClient, task: ClaimedTask) -> bool:
    """Whether the rendered page of ``task``'s procedure is still missing its screenshot."""
    return bool(client.artifacts.missing_screenshot(limit=1, catalogue_service_id=task.catalogue_service_id).items)
