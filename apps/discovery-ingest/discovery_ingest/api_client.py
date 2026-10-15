"""HTTP client for discovery machine routes."""

from __future__ import annotations

from collections.abc import Sequence

import httpx

from discovery_ingest.schemas import CatalogueBatchItem, CatalogueBatchRequest


class DiscoveryMachineApiError(Exception):
    """Machine API returned a non-success status."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"discovery machine API {status_code}: {detail}")


class DiscoveryMachineClient:
    """Post catalogue batch upserts with ``X-API-Key``."""

    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    def post_catalogue_batches(self, items: Sequence[CatalogueBatchItem], *, batch_size: int = 50) -> None:
        """Upsert items in chunks of at most ``batch_size``."""
        if batch_size < 1 or batch_size > 50:
            raise ValueError("batch_size must be between 1 and 50")
        chunk: list[CatalogueBatchItem] = []
        for item in items:
            chunk.append(item)
            if len(chunk) >= batch_size:
                self._post_batch(chunk)
                chunk = []
        if chunk:
            self._post_batch(chunk)

    def _post_batch(self, items: list[CatalogueBatchItem]) -> None:
        body = CatalogueBatchRequest(items=items)
        url = f"{self._base_url}/api/v1/discovery/machine/catalogue/batch"
        with httpx.Client(trust_env=True, timeout=60.0) as client:
            response = client.post(
                url,
                json=body.model_dump(mode="json"),
                headers={"X-API-Key": self._api_key},
            )
        if response.status_code >= 400:
            detail = response.text
            raise DiscoveryMachineApiError(response.status_code, detail)


def _post_catalogue_batches(
    base_url: str,
    api_key: str,
    items: Sequence[CatalogueBatchItem],
    *,
    batch_size: int = 50,
) -> None:
    """Upsert catalogue items via the discovery machine API."""
    client = DiscoveryMachineClient(base_url, api_key)
    client.post_catalogue_batches(items, batch_size=batch_size)
