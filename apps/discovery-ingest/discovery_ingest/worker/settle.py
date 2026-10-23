"""Settle a claimed task as failed: one place that builds the fail call."""

from __future__ import annotations

from uuid import UUID

from discovery_ingest.api_client import DiscoveryMachineClient
from discovery_ingest.worker.outcome import FetchOutcome


def fail_from_outcome(client: DiscoveryMachineClient, task_id: UUID, outcome: FetchOutcome) -> str:
    """Fail ``task_id`` with the reason and retryability of a failed fetch ``outcome``."""
    client.fail_task(task_id, error=outcome.failure_message, retryable=outcome.retryable)
    return "failed"


def fail_permanently(client: DiscoveryMachineClient, task_id: UUID, error: str) -> str:
    """Fail ``task_id`` with ``error`` and no retry: the cause is not transient."""
    client.fail_task(task_id, error=error, retryable=False)
    return "failed"
