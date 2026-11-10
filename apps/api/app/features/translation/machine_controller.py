"""HTTP handlers of the translation task machine routes: workers claim German units and post translated text."""

from __future__ import annotations

from litestar import Controller, get, post
from litestar.status_codes import HTTP_200_OK

from app.features.auth.principal import MachinePrincipal
from app.features.discovery.db_headroom import DB_WRITE_GUARDS
from app.features.discovery.guards import require_discovery_machine
from app.features.translation.queue import TranslationQueue
from app.features.translation.service import TranslationCompletion
from app.schema.translation.machine import (
    MAX_BODY_BYTES,
    TranslationClaimRequest,
    TranslationClaimResponse,
    TranslationCompleteRequest,
    TranslationCompleteResponse,
    TranslationFailRequest,
    TranslationFailResponse,
    TranslationReleaseRequest,
    TranslationReleaseResponse,
    TranslationSummaryResponse,
)


class TranslationMachineController(Controller):
    """Lease translation tasks to a machine key and settle them."""

    path = "/"
    guards = [require_discovery_machine]
    request_max_body_size = MAX_BODY_BYTES

    @post("/claim", sync_to_thread=True, status_code=HTTP_200_OK, guards=DB_WRITE_GUARDS)
    def claim(
        self, translation_queue: TranslationQueue, machine_principal: MachinePrincipal, data: TranslationClaimRequest
    ) -> TranslationClaimResponse:
        """Lease pending translation tasks to the calling key, highest-priority candidates first."""
        return translation_queue.claim(machine_principal.api_key.id, data.limit)

    @post("/complete", sync_to_thread=True, status_code=HTTP_200_OK, guards=DB_WRITE_GUARDS)
    def complete(
        self,
        translation_completion: TranslationCompletion,
        machine_principal: MachinePrincipal,
        data: TranslationCompleteRequest,
    ) -> TranslationCompleteResponse:
        """Store the posted translations; each item answers ``stored``, ``stale``, ``rejected`` or ``unavailable``."""
        results = translation_completion.complete(machine_principal.api_key.id, data.items)
        return TranslationCompleteResponse(items=results)

    @post("/fail", sync_to_thread=True, status_code=HTTP_200_OK)
    def fail(
        self, translation_queue: TranslationQueue, machine_principal: MachinePrincipal, data: TranslationFailRequest
    ) -> TranslationFailResponse:
        """Record that a claimed task could not be translated."""
        return translation_queue.fail(machine_principal.api_key.id, data)

    @post("/release", sync_to_thread=True, status_code=HTTP_200_OK)
    def release(
        self, translation_queue: TranslationQueue, machine_principal: MachinePrincipal, data: TranslationReleaseRequest
    ) -> TranslationReleaseResponse:
        """Hand claimed tasks back to the queue without consuming an attempt."""
        return translation_queue.release(machine_principal.api_key.id, data.task_ids, data.reason)

    @get("/summary", sync_to_thread=True, status_code=HTTP_200_OK)
    def summary(self, translation_queue: TranslationQueue) -> TranslationSummaryResponse:
        """Count the queue and the store per locale so a workflow can stop early when nothing is ready."""
        return translation_queue.summary()
