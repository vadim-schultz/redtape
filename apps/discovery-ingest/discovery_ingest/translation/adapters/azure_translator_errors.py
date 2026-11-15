"""Azure failures onto the port's categories: the service's error code first, then its HTTP status; no key survives."""

from __future__ import annotations

import math
from typing import Final

import httpx
from pydantic import BaseModel, ValidationError

from discovery_ingest.translation.errors import (
    PermanentError,
    QuotaExceeded,
    RateLimited,
    TransientError,
    TranslationEngineError,
    Unauthorised,
)

REDACTED: Final = "[redacted]"
RETRY_AFTER_HEADER: Final = "Retry-After"

_BY_CODE: Final[dict[str, type[TranslationEngineError]]] = {
    "403001": QuotaExceeded,
    "429000": RateLimited,
    "429001": RateLimited,
    "429002": RateLimited,
}
"""Codes that decide the category on their own, before the status is looked at."""
_BY_STATUS: Final[dict[int, type[TranslationEngineError]]] = {
    401: Unauthorised,
    403: Unauthorised,
    408: TransientError,
    429: RateLimited,
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
    category = category_of(response.status_code, code)
    if category is RateLimited:
        return RateLimited(redacted(text, key), retry_after=retry_after_of(response))
    return category(redacted(text, key))


def is_rate_limited(response: httpx.Response) -> bool:
    """Whether a failed response is a throttle (one of the 429 codes, or HTTP 429); a success never is."""
    if response.is_success:
        return False
    code, _ = _envelope_of(response)
    return category_of(response.status_code, code) is RateLimited


def retry_after_of(response: httpx.Response) -> float | None:
    """Return the ``Retry-After`` of a response in seconds, or ``None`` when it is absent, not a number, or negative.

    An HTTP date is not read: the service's own answers use seconds, and anything else falls back to the transport's wait.
    """
    raw = response.headers.get(RETRY_AFTER_HEADER)
    try:
        seconds = None if raw is None else float(raw)
    except ValueError:
        return None
    return seconds if seconds is not None and math.isfinite(seconds) and seconds >= 0 else None


def _envelope_of(response: httpx.Response) -> tuple[str, str]:
    """Return the service's error code and message, or two empty strings when the body is not the usual envelope."""
    try:
        detail = _Envelope.model_validate_json(response.content).error
    except ValidationError:
        return "", ""
    return str(detail.code), detail.message
