"""Queue a render_page task after a fetch that found a real HTML page and the API's verdict asks for one."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from uuid import UUID

import httpx
from pydantic import ValidationError

from discovery_ingest.client import DiscoveryIngestClient, DiscoveryMachineApiError
from discovery_ingest.schemas import ClaimedTask, FetchLogAppendResponse, TaskEnqueueRequest
from discovery_ingest.worker.login_wall import url_looks_like_login
from discovery_ingest.worker.outcome import FetchOutcome


@dataclass(frozen=True, slots=True)
class RenderOrder:
    """A render to enqueue: the catalogue row, the page it reads, and the input key the API chose for it."""

    catalogue_service_id: UUID
    target_url: str
    input_key: str | None


def _earns_a_render(outcome: FetchOutcome) -> bool:
    """Decide whether a 200 ``text/html`` page with a non-login final URL earns a render; the plain fetch stays the gate (D19)."""
    is_html = (outcome.content_type or "").lower().startswith("text/html")
    final = outcome.final_url
    return outcome.http_status == 200 and is_html and final is not None and not url_looks_like_login(final)


def _should_enqueue(outcome: FetchOutcome, verdict: FetchLogAppendResponse) -> bool:
    """Whether the fetch earns a render: a plain HTML page, and the API's verdict asks for one (changed or aged out)."""
    return _earns_a_render(outcome) and verdict.render_due


def render_order(task: ClaimedTask, outcome: FetchOutcome, verdict: FetchLogAppendResponse) -> RenderOrder | None:
    """Return the render the fetch earns, or ``None`` when the page is not a plain HTML page or the verdict asks for none."""
    if not _should_enqueue(outcome, verdict):
        return None
    return RenderOrder(
        catalogue_service_id=task.catalogue_service_id,
        target_url=str(outcome.final_url),
        input_key=verdict.render_input_key,
    )


def enqueue_render(client: DiscoveryIngestClient, order: RenderOrder) -> bool:
    """Enqueue the render; return false when the enqueue failed (logged, never raised)."""
    try:
        request = TaskEnqueueRequest(
            catalogue_service_id=order.catalogue_service_id,
            kind="render_page",
            target_url=order.target_url,
            input_key=order.input_key,
        )
        client.tasks.enqueue(request)
    except (DiscoveryMachineApiError, httpx.HTTPError, ValidationError) as err:
        print(f"render enqueue failed for {order.target_url}: {err}", file=sys.stderr)
        return False
    return True
