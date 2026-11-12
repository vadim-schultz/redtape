"""The Azure Translator transport: one POST per request, paced by the throttle, and every failure mapped onto the port.

The key travels only in the subscription header. Any text that goes into an error has the key replaced first.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

import httpx
from pydantic import BaseModel, ValidationError

from discovery_ingest.browser.throttle import Throttle
from discovery_ingest.translation.errors import (
    PermanentError,
    QuotaExceeded,
    TransientError,
    TranslationEngineError,
    Unauthorised,
    UnusableOutputError,
)

USAGE_HEADER: Final = "X-metered-usage"
"""The characters the service billed for one request."""
REDACTED: Final = "[redacted]"


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


_BY_CODE: Final[Mapping[str, type[TranslationEngineError]]] = {
    "403001": QuotaExceeded,
    "429000": TransientError,
    "429001": TransientError,
    "429002": TransientError,
}
"""Service error codes that decide the category on their own; a code wins over the status."""
_BY_STATUS: Final[Mapping[int, type[TranslationEngineError]]] = {
    401: Unauthorised,
    403: Unauthorised,
    408: TransientError,
    429: TransientError,
}


def category_of(status: int, code: str) -> type[TranslationEngineError]:
    """Return the port error for a failed request: the code first, then the status, then 5xx as transient."""
    if code in _BY_CODE:
        return _BY_CODE[code]
    if status in _BY_STATUS:
        return _BY_STATUS[status]
    return TransientError if status >= 500 else PermanentError


class _ErrorDetail(BaseModel):
    code: str | int = ""
    message: str = ""


class _ErrorBody(BaseModel):
    error: _ErrorDetail


class AzureTransport:
    """Send one translate request at a time and return its answer, or raise the port error of the failure."""

    def __init__(self, connection: AzureConnection, http: httpx.Client, throttle: Throttle) -> None:
        """Keep the connection, the HTTP client and the throttle that spaces the calls."""
        self._connection = connection
        self._http = http
        self._throttle = throttle

    def send(self, body: Mapping[str, object]) -> Reply:
        """POST ``body``; return the answer and the billed characters, or raise a port error with the key removed."""
        with self._throttle:
            try:
                response = self._http.post(self._url(), params=self._params(), json=body, headers=self._headers())
            except httpx.TransportError as err:
                raise TransientError(self._scrub(f"Azure Translator did not answer: {err}")) from err
        if response.is_success:
            return Reply(self._json(response), _metered(response))
        raise self._failure(response)

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

    def _json(self, response: httpx.Response) -> object:
        try:
            body: object = response.json()
        except ValueError as err:
            raise UnusableOutputError("the Azure answer is not JSON") from err
        return body

    def _failure(self, response: httpx.Response) -> TranslationEngineError:
        code, detail = _error_of(response)
        category = category_of(response.status_code, code)
        text = f"Azure Translator answered HTTP {response.status_code} ({code or 'no code'}): {detail}"
        return category(self._scrub(text))

    def _scrub(self, text: str) -> str:
        return text.replace(self._connection.key, REDACTED) if self._connection.key else text


def _error_of(response: httpx.Response) -> tuple[str, str]:
    """Return the service's error code and message, or empty strings when the body is not the usual envelope."""
    try:
        error = _ErrorBody.model_validate_json(response.content).error
    except ValidationError:
        return "", ""
    return str(error.code), error.message


def _metered(response: httpx.Response) -> float | None:
    raw = response.headers.get(USAGE_HEADER)
    try:
        return None if raw is None else float(raw)
    except ValueError:
        return None
