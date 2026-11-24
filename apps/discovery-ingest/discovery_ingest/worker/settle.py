"""Settle a claimed task as failed: one place that builds the fail call."""

from __future__ import annotations

from uuid import UUID

from discovery_ingest.client import DiscoveryIngestClient, DiscoveryMachineApiError
from discovery_ingest.schemas import FailureClass
from discovery_ingest.worker.outcome import FetchFailure, FetchOutcome

HTTP_NOT_FOUND = 404


def retry_class(retryable: bool) -> FailureClass:
    """Return ``transient`` for a failure the API may retry, ``permanent`` for one it must not."""
    return "transient" if retryable else "permanent"


def outcome_failure_class(outcome: FetchOutcome) -> FailureClass:
    """Return the class of a failed fetch: a robots block or a 404 is named, any other failure follows its retryability."""
    if outcome.failure is FetchFailure.ROBOTS_DISALLOWED:
        return "robots"
    if outcome.http_status == HTTP_NOT_FOUND:
        return "not_found"
    return retry_class(outcome.retryable)


def fail_from_outcome(client: DiscoveryIngestClient, task_id: UUID, outcome: FetchOutcome) -> str:
    """Fail ``task_id`` with the reason, retryability and class of a failed fetch ``outcome``."""
    client.tasks.fail(
        task_id,
        error=outcome.failure_message,
        retryable=outcome.retryable,
        failure_class=outcome_failure_class(outcome),
    )
    return "failed"


def fail_with(client: DiscoveryIngestClient, task_id: UUID, error: str, *, retryable: bool) -> str:
    """Fail ``task_id`` with ``error``; the API re-pends it when ``retryable`` and attempts remain."""
    client.tasks.fail(task_id, error=error, retryable=retryable, failure_class=retry_class(retryable))
    return "failed"


def fail_permanently(client: DiscoveryIngestClient, task_id: UUID, error: str) -> str:
    """Fail ``task_id`` with ``error`` and no retry: the cause is not transient."""
    return fail_with(client, task_id, error, retryable=False)


def fail_from_api_error(client: DiscoveryIngestClient, task_id: UUID, err: DiscoveryMachineApiError) -> str:
    """Fail ``task_id`` with the API's reason; only a server error (5xx) is worth a retry."""
    return fail_with(client, task_id, err.detail, retryable=err.status_code >= 500)
