"""``catalogue refresh``: re-enqueue the stale portal pages of the weekly run, within the bound and the weekly page caps."""

from __future__ import annotations

from collections.abc import Sequence

from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.operations.requeue import Counts, enqueue_counted
from discovery_ingest.schemas import StaleFetchRead, TaskEnqueueRequest

DEFAULT_GOVDATA_MAX_PAGES = 150
"""The GovData page cap the weekly workflow starts from; the refresh bound never exceeds it."""
DEFAULT_PVOG_MAX_PAGES = 50
"""The PVOG page cap the weekly workflow starts from; the refresh bound never exceeds it."""


def refresh_bound(requested: int, *, page_caps: Sequence[int]) -> int:
    """Return how many stale pages one weekly run may refresh: the request, never above the smallest page cap."""
    return max(0, min((requested, *page_caps)))


def refresh_stale_fetches(client: DiscoveryIngestClient, *, max_rows: int, page_caps: Sequence[int]) -> Counts:
    """Enqueue a fetch_url under the week's key for up to the bound of stale pages; a bound of zero makes no request.

    A refused listing raises the API error. A refused enqueue is counted as failed and the run goes on.
    """
    bound = refresh_bound(max_rows, page_caps=page_caps)
    counts = Counts()
    if bound == 0:
        return counts
    page = client.catalogue.stale_fetches(limit=bound)
    counts.pages = len(page.items)
    for row in page.items:
        enqueue_counted(client, _refresh_request(row, page.input_key), counts)
    return counts


def _refresh_request(row: StaleFetchRead, input_key: str) -> TaskEnqueueRequest:
    """Return the fetch_url enqueue for one stale page, keyed by the week so a repeat in the same week is a no-op."""
    return TaskEnqueueRequest(
        catalogue_service_id=row.catalogue_service_id,
        kind="fetch_url",
        target_url=row.target_url,
        input_key=input_key,
    )
