"""Settle a claimed task as failed: one place that builds the fail call."""

from __future__ import annotations

from uuid import UUID

from discovery_ingest.api_client import DiscoveryMachineApiError, DiscoveryMachineClient
from discovery_ingest.worker.outcome import FetchOutcome


def fail_from_outcome(client: DiscoveryMachineClient, task_id: UUID, outcome: FetchOutcome) -> str:
    """Fail ``task_id`` with the reason and retryability of a failed fetch ``outcome``."""
    client.fail_task(task_id, error=outcome.failure_message, retryable=outcome.retryable)
    return "failed"


def fail_with(client: DiscoveryMachineClient, task_id: UUID, error: str, *, retryable: bool) -> str:
    """Fail ``task_id`` with ``error``; the API re-pends it when ``retryable`` and attempts remain."""
    client.fail_task(task_id, error=error, retryable=retryable)
    return "failed"


def fail_permanently(client: DiscoveryMachineClient, task_id: UUID, error: str) -> str:
    """Fail ``task_id`` with ``error`` and no retry: the cause is not transient."""
    return fail_with(client, task_id, error, retryable=False)


def fail_from_api_error(client: DiscoveryMachineClient, task_id: UUID, err: DiscoveryMachineApiError) -> str:
    """Fail ``task_id`` with the API's reason; only a server error (5xx) is worth a retry."""
    client.fail_task(task_id, error=err.detail, retryable=err.status_code >= 500)
    return "failed"
