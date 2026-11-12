"""Azure failures onto the port's categories: the service's error code first, then its HTTP status; no key survives."""

from __future__ import annotations

from typing import Final

import httpx
from pydantic import BaseModel, ValidationError

from discovery_ingest.translation.errors import (
    PermanentError,
    QuotaExceeded,
    TransientError,
    TranslationEngineError,
    Unauthorised,
)

REDACTED: Final = "[redacted]"

_BY_CODE: Final[dict[str, type[TranslationEngineError]]] = {
    "403001": QuotaExceeded,
    "429000": TransientError,
    "429001": TransientError,
    "429002": TransientError,
}
"""Codes that decide the category on their own, before the status is looked at."""
_BY_STATUS: Final[dict[int, type[TranslationEngineError]]] = {
    401: Unauthorised,
    403: Unauthorised,
    408: TransientError,
    429: TransientError,
}


class _Detail(BaseModel):
    code: str | int = ""
    message: str = ""


class _Envelope(BaseModel):
    error: _Detail


def redacted(text: str, key: str) -> str:
    """Return ``text`` with every occurrence of the subscription key replaced."""
    return text.replace(key, REDACTED) if key else text


def category_of(status: int, code: str) -> type[TranslationEngineError]:
    """Return the port error for a failed request: the code, then the status; any other 5xx is transient."""
    if code in _BY_CODE:
        return _BY_CODE[code]
    if status in _BY_STATUS:
        return _BY_STATUS[status]
    return TransientError if status >= 500 else PermanentError


def port_error(response: httpx.Response, key: str) -> TranslationEngineError:
    """Return the port error for a failed response; its text names the status and the code, and never the key."""
    code, message = _envelope_of(response)
    text = f"Azure Translator answered HTTP {response.status_code} ({code or 'no code'}): {message}"
    return category_of(response.status_code, code)(redacted(text, key))


def _envelope_of(response: httpx.Response) -> tuple[str, str]:
    """Return the service's error code and message, or two empty strings when the body is not the usual envelope."""
    try:
        detail = _Envelope.model_validate_json(response.content).error
    except ValidationError:
        return "", ""
    return str(detail.code), detail.message
