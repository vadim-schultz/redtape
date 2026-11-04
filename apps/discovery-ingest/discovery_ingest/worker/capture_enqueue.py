"""Queue a capture_screenshot task for a page an extractor found documents on (decision D13)."""

from __future__ import annotations

import sys
from uuid import UUID

import httpx
from pydantic import ValidationError

from discovery_ingest.client import DiscoveryIngestClient, DiscoveryMachineApiError
from discovery_ingest.schemas import ClaimedTask, TaskEnqueueRequest

CAPTURE_PRIORITY = 300
"""Claimed after renders (100) and extractions, because the queue takes lower numbers first."""
CAPTURE_INPUT_KEY = "shot@1"
"""The same for every extractor and version, so one page keeps one capture however often it is extracted."""


def capture_request(catalogue_service_id: UUID, target_url: str) -> TaskEnqueueRequest:
    """Return the ``capture_screenshot`` enqueue request for the page ``target_url`` of one catalogue row."""
    return TaskEnqueueRequest(
        catalogue_service_id=catalogue_service_id,
        kind="capture_screenshot",
        target_url=target_url,
        priority=CAPTURE_PRIORITY,
        input_key=CAPTURE_INPUT_KEY,
    )


def enqueue_screenshot_for_mentions(client: DiscoveryIngestClient, task: ClaimedTask) -> bool:
    """Enqueue ``capture_screenshot`` for the page ``task`` extracted; return false when it failed (logged, never raised).

    Call it after at least one mention was posted, from any extractor handler. The page is ``task.target_url``, the
    artifact's ``source_url``, which already is the redirect-resolved URL of the plain fetch.
    """
    try:
        client.tasks.enqueue(capture_request(task.catalogue_service_id, task.target_url))
    except (DiscoveryMachineApiError, httpx.HTTPError, ValidationError) as err:
        print(f"capture enqueue failed for {task.target_url}: {err}", file=sys.stderr)
        return False
    return True
