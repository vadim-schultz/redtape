"""Task routes: claim, summarise, enqueue and settle the discovery work queue."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from pydantic import JsonValue

from discovery_ingest.client.http_client import MachineHttpClient
from discovery_ingest.schemas import (
    DiscoveryTaskKind,
    FailureClass,
    FetchLogAppendRequest,
    FetchLogAppendResponse,
    TaskClaimRequest,
    TaskClaimResponse,
    TaskEnqueueRequest,
    TaskEnqueueResponse,
    TaskSummary,
    TextExtractedQuery,
    TextExtractedResponse,
)


class TasksAPI:
    """Claim, read, enqueue and settle discovery tasks."""

    def __init__(self, http: MachineHttpClient) -> None:
        """Keep the shared HTTP client."""
        self._http = http

    def claim(self, *, limit: int, kinds: Sequence[DiscoveryTaskKind]) -> TaskClaimResponse:
        """Claim pending discovery tasks of ``kinds`` for this API key."""
        body = TaskClaimRequest(limit=limit, kinds=list(kinds))
        return self._http.request_model(TaskClaimResponse, "POST", "/tasks/claim", json=body.model_dump(mode="json"))

    def summary(self, *, kinds: Sequence[DiscoveryTaskKind]) -> TaskSummary:
        """Return queue counts for ``kinds`` without leasing anything."""
        return self._http.request_model(TaskSummary, "GET", "/tasks/summary", params={"kinds": list(kinds)})

    def enqueue(self, body: TaskEnqueueRequest) -> TaskEnqueueResponse:
        """Enqueue a follow-up task; an equivalent existing task is returned instead."""
        return self._http.request_model(
            TaskEnqueueResponse, "POST", "/tasks", json=body.model_dump(mode="json", exclude_none=True)
        )

    def append_fetch(self, task_id: UUID, body: FetchLogAppendRequest) -> FetchLogAppendResponse:
        """Append a fetch log row for a claimed task and return the render verdict the API answers with."""
        return self._http.request_model(
            FetchLogAppendResponse, "POST", f"/tasks/{task_id}/fetches", json=body.model_dump(mode="json")
        )

    def complete(self, task_id: UUID, *, note: str | None = None, text_hash: str | None = None) -> None:
        """Mark a claimed task completed; ``note`` says why nothing was produced, ``text_hash`` names the cleaned text read."""
        body: dict[str, JsonValue] = {}
        if note is not None:
            body["note"] = note
        if text_hash is not None:
            body["text_hash"] = text_hash
        self._http.request("POST", f"/tasks/{task_id}/complete", json=body or None)

    def text_extracted(self, query: TextExtractedQuery) -> bool:
        """Return whether a completed extraction of the page under the query's input key already read its cleaned text."""
        answer = self._http.request_model(
            TextExtractedResponse, "GET", "/tasks/text-extracted", params=query.model_dump(mode="json")
        )
        return answer.extracted

    def release(self, task_id: UUID, reason: str, *, not_before: datetime | None = None) -> None:
        """Hand a claimed task back to ``pending`` without consuming an attempt (a limit stopped the work)."""
        body: dict[str, JsonValue] = {
            "reason": reason,
            **({"not_before": not_before.isoformat()} if not_before else {}),
        }
        self._http.request("POST", f"/tasks/{task_id}/release", json=body)

    def fail(
        self, task_id: UUID, *, error: str, retryable: bool = False, failure_class: FailureClass | None = None
    ) -> None:
        """Fail a claimed task with ``error`` and its ``failure_class``; the API re-pends it when ``retryable`` and attempts remain."""
        body: dict[str, JsonValue] = {"error": error, "retryable": retryable}
        if failure_class is not None:
            body["failure_class"] = failure_class
        self._http.request("POST", f"/tasks/{task_id}/fail", json=body)
