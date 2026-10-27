"""Hand claimed tasks back to the queue when a limit, not the page, stopped the work."""

from __future__ import annotations

import sys
from collections.abc import Sequence

import httpx

from discovery_ingest.api_client import DiscoveryMachineApiError, DiscoveryMachineClient
from discovery_ingest.schemas import ClaimedTask

MAX_REASON = 1000


def release_tasks(client: DiscoveryMachineClient, tasks: Sequence[ClaimedTask], reason: str) -> int:
    """Release every task in ``tasks``; return how many the API took back (a failure is logged, never raised)."""
    return sum(_release(client, task, reason[:MAX_REASON]) for task in tasks)


def _release(client: DiscoveryMachineClient, task: ClaimedTask, reason: str) -> int:
    try:
        client.release_task(task.id, reason)
    except (DiscoveryMachineApiError, httpx.HTTPError) as err:
        print(f"release of task {task.id} failed: {err}", file=sys.stderr)
        return 0
    return 1
