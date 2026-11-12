"""Machine client for the snapshot routes: claim pages, post their blocks, fail, release and count the page queue."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from discovery_ingest.client.http_client import MachineHttpClient
from discovery_ingest.schemas import (
    SnapshotClaimRequest,
    SnapshotClaimResponse,
    SnapshotCompleteItem,
    SnapshotCompleteRequest,
    SnapshotCompleteResponse,
    SnapshotSummaryResponse,
)
from discovery_ingest.translation_models import (
    TranslationFailRequest,
    TranslationFailResponse,
    TranslationReleaseRequest,
    TranslationReleaseResponse,
)


class SnapshotsAPI:
    """The machine routes of the snapshot queue; a refusal raises :class:`DiscoveryMachineApiError`."""

    def __init__(self, http: MachineHttpClient) -> None:
        """Keep the shared HTTP client."""
        self._http = http

    def claim(self, *, limit: int) -> SnapshotClaimResponse:
        """Lease up to ``limit`` ready page tasks to this API key, each with its latest snapshot's reference."""
        body = SnapshotClaimRequest(limit=limit)
        return self._http.request_model(
            SnapshotClaimResponse, "POST", "/snapshots/claim", json=body.model_dump(mode="json")
        )

    def complete(self, items: Sequence[SnapshotCompleteItem]) -> SnapshotCompleteResponse:
        """Post page results; each item answers ``stored``, ``unchanged``, ``skipped``, ``stale``, ``rejected`` or ``unavailable``."""
        body = SnapshotCompleteRequest(items=list(items))
        return self._http.request_model(
            SnapshotCompleteResponse,
            "POST",
            "/snapshots/complete",
            json=body.model_dump(mode="json", exclude_unset=True),
        )

    def fail(self, task_id: UUID, *, error: str, retryable: bool = False) -> TranslationFailResponse:
        """Fail a claimed page task; the API re-pends it when ``retryable`` and attempts remain (409: not held by this key)."""
        body = TranslationFailRequest(task_id=task_id, error=error[:1000], retryable=retryable)
        return self._http.request_model(
            TranslationFailResponse, "POST", "/snapshots/fail", json=body.model_dump(mode="json")
        )

    def release(self, task_ids: Sequence[UUID], reason: str) -> TranslationReleaseResponse:
        """Hand claimed page tasks back without consuming an attempt; tasks this key does not hold are ``skipped``."""
        body = TranslationReleaseRequest(task_ids=list(task_ids), reason=reason[:1000])
        return self._http.request_model(
            TranslationReleaseResponse, "POST", "/snapshots/release", json=body.model_dump(mode="json")
        )

    def summary(self) -> SnapshotSummaryResponse:
        """Count the page queue and the stored pages per target locale without leasing anything."""
        return self._http.request_model(SnapshotSummaryResponse, "GET", "/snapshots/summary")
