"""Embedding routes: claim text, post vectors, settle failures, hand tasks back and count the queue."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from discovery_ingest.client.http_client import MachineHttpClient
from discovery_ingest.embedding_models import (
    EmbeddingClaimRequest,
    EmbeddingClaimResponse,
    EmbeddingCompleteItem,
    EmbeddingCompleteRequest,
    EmbeddingCompleteResponse,
    EmbeddingFailRequest,
    EmbeddingFailResponse,
    EmbeddingReleaseRequest,
    EmbeddingReleaseResponse,
    EmbeddingSummary,
)


class EmbeddingsAPI:
    """The machine routes of the embedding task queue; a refusal raises :class:`DiscoveryMachineApiError`."""

    def __init__(self, http: MachineHttpClient) -> None:
        """Keep the shared HTTP client."""
        self._http = http

    def claim(self, model: str, *, limit: int) -> EmbeddingClaimResponse:
        """Lease up to ``limit`` ready tasks of ``model`` to this API key."""
        body = EmbeddingClaimRequest(model=model, limit=limit)
        return self._http.request_model(
            EmbeddingClaimResponse, "POST", "/embeddings/claim", json=body.model_dump(mode="json")
        )

    def complete(self, items: Sequence[EmbeddingCompleteItem]) -> EmbeddingCompleteResponse:
        """Post computed vectors; every item answers ``stored``, ``stale`` or ``rejected``."""
        body = EmbeddingCompleteRequest(items=list(items))
        return self._http.request_model(
            EmbeddingCompleteResponse, "POST", "/embeddings/complete", json=body.model_dump(mode="json")
        )

    def fail(self, task_id: UUID, *, error: str, retryable: bool = False) -> EmbeddingFailResponse:
        """Fail a claimed task; the API re-pends it when ``retryable`` and attempts remain (409: not held by this key)."""
        body = EmbeddingFailRequest(task_id=task_id, error=error[:1000], retryable=retryable)
        return self._http.request_model(
            EmbeddingFailResponse, "POST", "/embeddings/fail", json=body.model_dump(mode="json")
        )

    def release(self, task_ids: Sequence[UUID], reason: str) -> EmbeddingReleaseResponse:
        """Hand claimed tasks back without consuming an attempt; tasks this key does not hold are ``skipped``."""
        body = EmbeddingReleaseRequest(task_ids=list(task_ids), reason=reason[:1000])
        return self._http.request_model(
            EmbeddingReleaseResponse, "POST", "/embeddings/release", json=body.model_dump(mode="json")
        )

    def summary(self, model: str) -> EmbeddingSummary:
        """Count the queue of ``model`` without leasing anything."""
        return self._http.request_model(EmbeddingSummary, "GET", "/embeddings/summary", params={"model": model})
