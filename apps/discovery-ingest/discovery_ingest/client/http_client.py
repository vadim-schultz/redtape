"""Shared transport for the machine routes: one long-lived httpx client, one request method."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TypedDict, TypeVar, Unpack

import httpx
from pydantic import BaseModel, JsonValue, SecretStr

from discovery_ingest.client.errors import DiscoveryMachineApiError

MACHINE_PREFIX = "/api/v1/discovery/machine"
REQUEST_TIMEOUT_SECONDS = 60.0
"""Unchanged from the per-request clients; naming the value is not tuning it."""

M = TypeVar("M", bound=BaseModel)


class RequestOptions(TypedDict, total=False):
    """Keyword options of one machine request; ``allow`` lists statuses that are answers, not errors."""

    json: JsonValue
    params: Mapping[str, str | int | list[str]]
    data: Mapping[str, str]
    files: Mapping[str, tuple[str, bytes, str]]
    allow: tuple[int, ...]


class MachineHttpClient:
    """Own the HTTP connection to the machine routes and map failed statuses to ``DiscoveryMachineApiError``."""

    def __init__(self, base_url: str, api_key: SecretStr, *, transport: httpx.BaseTransport | None = None) -> None:
        """Open the connection pool under ``base_url`` with the key as the ``X-API-Key`` default header."""
        self._secret = api_key.get_secret_value()
        self._client = httpx.Client(
            base_url=f"{base_url.rstrip('/')}{MACHINE_PREFIX}/",
            headers={"X-API-Key": self._secret},
            timeout=REQUEST_TIMEOUT_SECONDS,
            trust_env=True,
            transport=transport,
        )

    def request(self, method: str, path: str, **options: Unpack[RequestOptions]) -> httpx.Response:
        """Send one request to ``path`` under the machine prefix and return it unless its status is an error."""
        response = self._client.request(
            method,
            path,
            json=options.get("json"),
            params=options.get("params"),
            data=options.get("data"),
            files=options.get("files"),
        )
        if response.status_code >= 400 and response.status_code not in options.get("allow", ()):
            raise DiscoveryMachineApiError.from_response(response, self._secret)
        return response

    def request_model(self, model: type[M], method: str, path: str, **options: Unpack[RequestOptions]) -> M:
        """Send one request and validate the JSON answer as ``model``."""
        return model.model_validate(self.request(method, path, **options).json())

    def close(self) -> None:
        """Release the connection pool."""
        self._client.close()
