"""HTTP handlers of the snapshot machine routes: workers claim page translations and post blocks of text."""

from __future__ import annotations

from litestar import Controller, get, post
from litestar.status_codes import HTTP_200_OK

from app.features.auth.principal import MachinePrincipal
from app.features.discovery.db_headroom import DB_WRITE_GUARDS
from app.features.discovery.guards import require_discovery_machine
from app.features.translation.snapshot_completion import SnapshotCompletion
from app.features.translation.snapshot_queue import SnapshotQueue
from app.schema.translation.machine import (
    MAX_BODY_BYTES,
    TranslationFailRequest,
    TranslationFailResponse,
    TranslationReleaseRequest,
    TranslationReleaseResponse,
)
from app.schema.translation.snapshot_machine import (
    SnapshotClaimRequest,
    SnapshotClaimResponse,
    SnapshotCompleteRequest,
    SnapshotCompleteResponse,
    SnapshotSummaryResponse,
)


class SnapshotMachineController(Controller):
    """Lease page translation tasks to a machine key and settle them."""

    path = "/"
    guards = [require_discovery_machine]
    request_max_body_size = MAX_BODY_BYTES

    @post("/claim", sync_to_thread=True, status_code=HTTP_200_OK, guards=DB_WRITE_GUARDS)
    def claim(
        self, snapshot_queue: SnapshotQueue, machine_principal: MachinePrincipal, data: SnapshotClaimRequest
    ) -> SnapshotClaimResponse:
        """Lease pending page tasks to the calling key, highest-priority pages first, each with its latest snapshot."""
        return snapshot_queue.claim(machine_principal.api_key.id, data.limit)

    @post("/complete", sync_to_thread=True, status_code=HTTP_200_OK, guards=DB_WRITE_GUARDS)
    def complete(
        self,
        snapshot_completion: SnapshotCompletion,
        machine_principal: MachinePrincipal,
        data: SnapshotCompleteRequest,
    ) -> SnapshotCompleteResponse:
        """Store the posted page results; each item answers stored, unchanged, skipped, stale, rejected or unavailable."""
        return SnapshotCompleteResponse(items=snapshot_completion.complete(machine_principal.api_key.id, data.items))

    @post("/fail", sync_to_thread=True, status_code=HTTP_200_OK)
    def fail(
        self, snapshot_queue: SnapshotQueue, machine_principal: MachinePrincipal, data: TranslationFailRequest
    ) -> TranslationFailResponse:
        """Record that a claimed page task could not be translated."""
        return snapshot_queue.fail(machine_principal.api_key.id, data)

    @post("/release", sync_to_thread=True, status_code=HTTP_200_OK)
    def release(
        self, snapshot_queue: SnapshotQueue, machine_principal: MachinePrincipal, data: TranslationReleaseRequest
    ) -> TranslationReleaseResponse:
        """Hand claimed page tasks back to the queue without consuming an attempt."""
        return snapshot_queue.release(machine_principal.api_key.id, data.task_ids, data.reason)

    @get("/summary", sync_to_thread=True, status_code=HTTP_200_OK)
    def summary(self, snapshot_queue: SnapshotQueue) -> SnapshotSummaryResponse:
        """Count the page queue and the stored pages per locale so a workflow can stop early when nothing is ready."""
        return snapshot_queue.summary()
