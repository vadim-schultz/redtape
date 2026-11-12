"""The Azure Translator transport: one POST per request, paced by the throttle; the answer or the port error.

The key travels only in the subscription header and is removed from every error text.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

import httpx

from discovery_ingest.browser.throttle import Throttle
from discovery_ingest.translation.adapters.azure_translator_errors import port_error, redacted
from discovery_ingest.translation.errors import TransientError, UnusableOutputError

USAGE_HEADER: Final = "X-metered-usage"
"""The response header that carries the characters the service billed for one request."""


@dataclass(frozen=True, slots=True)
class AzureConnection:
    """Where the Translator is and how it is called: the endpoint, the API version, the key and the resource region."""

    endpoint: str
    api_version: str
    key: str
    region: str


@dataclass(frozen=True, slots=True)
class Reply:
    """The JSON body of a successful request, and the characters it billed (``None`` when the header is absent)."""

    body: object
    metered: float | None


class AzureTransport:
    """Send one translate request at a time and return its answer, or raise the port error of the failure."""

    def __init__(self, connection: AzureConnection, throttle: Throttle, http: httpx.Client | None = None) -> None:
        """Keep the connection and the throttle that spaces the calls; without a client, one that reads the proxy settings."""
        self._connection = connection
        self._throttle = throttle
        self._http = http if http is not None else httpx.Client(trust_env=True)

    def send(self, body: Mapping[str, object]) -> Reply:
        """POST ``body``; return the answer and the billed characters, or raise a port error with the key removed."""
        response = self._post(body)
        if not response.is_success:
            raise port_error(response, self._connection.key)
        return Reply(_json_of(response), _metered(response))

    def _post(self, body: Mapping[str, object]) -> httpx.Response:
        with self._throttle:
            try:
                return self._http.post(self._url(), params=self._params(), json=body, headers=self._headers())
            except httpx.TransportError as err:
                raise TransientError(redacted(f"Azure Translator did not answer: {err}", self._connection.key)) from err

    def _url(self) -> str:
        return f"{self._connection.endpoint.rstrip('/')}/translate"

    def _params(self) -> dict[str, str]:
        return {"api-version": self._connection.api_version}

    def _headers(self) -> dict[str, str]:
        return {
            "Ocp-Apim-Subscription-Key": self._connection.key,
            "Ocp-Apim-Subscription-Region": self._connection.region,
            "Content-Type": "application/json",
            "X-ClientTraceId": str(uuid.uuid4()),
        }


def _json_of(response: httpx.Response) -> object:
    try:
        body: object = response.json()
    except ValueError as err:
        raise UnusableOutputError("the Azure answer is not JSON") from err
    return body


def _metered(response: httpx.Response) -> float | None:
    raw = response.headers.get(USAGE_HEADER)
    try:
        return None if raw is None else float(raw)
    except ValueError:
        return None
