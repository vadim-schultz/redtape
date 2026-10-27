"""Queue a render_page task after a fetch that found a real HTML page."""

from __future__ import annotations

import sys

import httpx
from pydantic import ValidationError

from discovery_ingest.api_client import DiscoveryMachineApiError, DiscoveryMachineClient
from discovery_ingest.schemas import ClaimedTask, TaskEnqueueRequest
from discovery_ingest.worker.login_wall import url_looks_like_login
from discovery_ingest.worker.outcome import FetchOutcome


def _earns_a_render(outcome: FetchOutcome) -> bool:
    """A 200 ``text/html`` page whose final URL is not a login URL; the plain fetch stays the gate (D19)."""
    is_html = (outcome.content_type or "").lower().startswith("text/html")
    final = outcome.final_url
    return outcome.http_status == 200 and is_html and final is not None and not url_looks_like_login(final)


def enqueue_render(client: DiscoveryMachineClient, task: ClaimedTask, outcome: FetchOutcome) -> bool:
    """Enqueue ``render_page`` for the fetched page; return false when the enqueue failed (logged, never raised)."""
    if not _earns_a_render(outcome):
        return True
    try:
        request = TaskEnqueueRequest(
            catalogue_service_id=task.catalogue_service_id, kind="render_page", target_url=str(outcome.final_url)
        )
        client.enqueue_task(request)
    except (DiscoveryMachineApiError, httpx.HTTPError, ValidationError) as err:
        print(f"render enqueue failed for {outcome.final_url}: {err}", file=sys.stderr)
        return False
    return True
