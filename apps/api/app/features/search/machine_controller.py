"""HTTP handlers of the embedding task machine routes: workers claim text, post vectors, never touch the database."""

from __future__ import annotations

from litestar import Controller, get, post
from litestar.status_codes import HTTP_200_OK

from app.features.auth.principal import MachinePrincipal
from app.features.discovery.db_headroom import DB_WRITE_GUARDS
from app.features.discovery.guards import require_discovery_machine
from app.features.search.complete import EmbeddingCompletion
from app.features.search.queue import EmbeddingQueue
from app.schema.search.machine import (
    MAX_BODY_BYTES,
    EmbeddingClaimRequest,
    EmbeddingClaimResponse,
    EmbeddingCompleteRequest,
    EmbeddingCompleteResponse,
    EmbeddingFailRequest,
    EmbeddingFailResponse,
    EmbeddingReleaseRequest,
    EmbeddingReleaseResponse,
    EmbeddingSummaryResponse,
)


class EmbeddingMachineController(Controller):
    """Lease embedding tasks to a machine key and settle them."""

    path = "/"
    guards = [require_discovery_machine]
    request_max_body_size = MAX_BODY_BYTES

    @post("/claim", sync_to_thread=True, status_code=HTTP_200_OK, guards=DB_WRITE_GUARDS)
    def claim(
        self, embedding_queue: EmbeddingQueue, machine_principal: MachinePrincipal, data: EmbeddingClaimRequest
    ) -> EmbeddingClaimResponse:
        """Lease pending embedding tasks of one model to the calling key."""
        return embedding_queue.claim(machine_principal.api_key.id, data.model, data.limit)

    @post("/complete", sync_to_thread=True, status_code=HTTP_200_OK, guards=DB_WRITE_GUARDS)
    def complete(
        self,
        embedding_completion: EmbeddingCompletion,
        machine_principal: MachinePrincipal,
        data: EmbeddingCompleteRequest,
    ) -> EmbeddingCompleteResponse:
        """Store the posted vectors; each item answers ``stored``, ``stale`` or ``rejected``."""
        results = embedding_completion.complete(machine_principal.api_key.id, data.items)
        return EmbeddingCompleteResponse(items=results)

    @post("/fail", sync_to_thread=True, status_code=HTTP_200_OK)
    def fail(
        self, embedding_queue: EmbeddingQueue, machine_principal: MachinePrincipal, data: EmbeddingFailRequest
    ) -> EmbeddingFailResponse:
        """Record that a claimed task could not be embedded."""
        return embedding_queue.fail(machine_principal.api_key.id, data)

    @post("/release", sync_to_thread=True, status_code=HTTP_200_OK)
    def release(
        self, embedding_queue: EmbeddingQueue, machine_principal: MachinePrincipal, data: EmbeddingReleaseRequest
    ) -> EmbeddingReleaseResponse:
        """Hand claimed tasks back to the queue without consuming an attempt."""
        return embedding_queue.release(machine_principal.api_key.id, data.task_ids, data.reason)

    @get("/summary", sync_to_thread=True, status_code=HTTP_200_OK)
    def summary(self, embedding_queue: EmbeddingQueue, model: str | None = None) -> EmbeddingSummaryResponse:
        """Count the queue so a workflow can stop early when nothing is ready."""
        return embedding_queue.summary(model)
