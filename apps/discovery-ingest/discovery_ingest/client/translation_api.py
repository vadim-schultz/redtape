"""Translation routes: claim German units, post translations, settle failures, hand tasks back and count the queue."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from discovery_ingest.client.http_client import MachineHttpClient
from discovery_ingest.translation_models import (
    PriorityBand,
    TranslationClaimRequest,
    TranslationClaimResponse,
    TranslationCompleteItem,
    TranslationCompleteRequest,
    TranslationCompleteResponse,
    TranslationFailRequest,
    TranslationFailResponse,
    TranslationReleaseRequest,
    TranslationReleaseResponse,
    TranslationSummary,
)


class TranslationsAPI:
    """The machine routes of the translation task queue; a refusal raises :class:`DiscoveryMachineApiError`."""

    def __init__(self, http: MachineHttpClient) -> None:
        """Keep the shared HTTP client."""
        self._http = http

    def claim(
        self, *, limit: int, engine: str | None = None, band: PriorityBand | None = None
    ) -> TranslationClaimResponse:
        """Lease up to ``limit`` ready tasks of the API's target locales to this API key, best candidates first.

        ``engine`` names the lane the API serves this claim from (absent: no lane) and ``band`` the priority range; an
        unset field is left out of the body, so a plain claim sends only the limit.
        """
        priority = PriorityBand() if band is None else band
        body = TranslationClaimRequest(
            limit=limit, engine=engine, priority_min=priority.minimum, priority_max=priority.maximum
        )
        return self._http.request_model(
            TranslationClaimResponse,
            "POST",
            "/translations/claim",
            json=body.model_dump(mode="json", exclude_none=True),
        )

    def complete(self, items: Sequence[TranslationCompleteItem]) -> TranslationCompleteResponse:
        """Post translated text; every item answers ``stored``, ``stale``, ``rejected`` or ``unavailable``."""
        body = TranslationCompleteRequest(items=list(items))
        return self._http.request_model(
            TranslationCompleteResponse, "POST", "/translations/complete", json=body.model_dump(mode="json")
        )

    def fail(self, task_id: UUID, *, error: str, retryable: bool = False) -> TranslationFailResponse:
        """Fail a claimed task; the API re-pends it when ``retryable`` and attempts remain (409: not held by this key)."""
        body = TranslationFailRequest(task_id=task_id, error=error[:1000], retryable=retryable)
        return self._http.request_model(
            TranslationFailResponse, "POST", "/translations/fail", json=body.model_dump(mode="json")
        )

    def release(self, task_ids: Sequence[UUID], reason: str) -> TranslationReleaseResponse:
        """Hand claimed tasks back without consuming an attempt; tasks this key does not hold are ``skipped``."""
        body = TranslationReleaseRequest(task_ids=list(task_ids), reason=reason[:1000])
        return self._http.request_model(
            TranslationReleaseResponse, "POST", "/translations/release", json=body.model_dump(mode="json")
        )

    def summary(self) -> TranslationSummary:
        """Count the queue and the store per target locale without leasing anything."""
        return self._http.request_model(TranslationSummary, "GET", "/translations/summary")
