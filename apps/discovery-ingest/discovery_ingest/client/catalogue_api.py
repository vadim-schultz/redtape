"""Catalogue routes: batch upserts, one catalogue row, and the entities and claims that hang under it."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from discovery_ingest.batch_dedup import dedupe_batch_items
from discovery_ingest.client.http_client import MachineHttpClient
from discovery_ingest.schemas import (
    CatalogueBatchItem,
    CatalogueBatchRequest,
    CatalogueMachineRead,
    ClaimAppendRequest,
    ClaimAppendResponse,
    EntityUpsertRequest,
    EntityUpsertResponse,
)

MAX_BATCH_SIZE = 50


class CatalogueAPI:
    """Upsert and read catalogue rows, entities and claims."""

    def __init__(self, http: MachineHttpClient) -> None:
        """Keep the shared HTTP client."""
        self._http = http

    def upsert_batches(self, items: Sequence[CatalogueBatchItem], *, batch_size: int = MAX_BATCH_SIZE) -> None:
        """Upsert ``items`` after collapsing duplicates, in requests of at most ``batch_size`` rows."""
        if batch_size < 1 or batch_size > MAX_BATCH_SIZE:
            raise ValueError(f"batch_size must be between 1 and {MAX_BATCH_SIZE}")
        deduped = dedupe_batch_items(items)
        for start in range(0, len(deduped), batch_size):
            body = CatalogueBatchRequest(items=deduped[start : start + batch_size])
            self._http.request("POST", "/catalogue/batch", json=body.model_dump(mode="json"))

    def get(self, catalogue_id: UUID) -> CatalogueMachineRead:
        """Load the minimal catalogue row that enrich workers read."""
        return self._http.request_model(CatalogueMachineRead, "GET", f"/catalogue/{catalogue_id}")

    def upsert_entity(self, body: EntityUpsertRequest) -> EntityUpsertResponse:
        """Upsert a discovery entity under a catalogue row."""
        return self._http.request_model(EntityUpsertResponse, "POST", "/entities", json=body.model_dump(mode="json"))

    def append_claim(self, body: ClaimAppendRequest) -> ClaimAppendResponse:
        """Append a discovery claim on an entity."""
        return self._http.request_model(ClaimAppendResponse, "POST", "/claims", json=body.model_dump(mode="json"))
