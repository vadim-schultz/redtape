"""Turn a Cloudflare response into a result or one of the browser errors (the error table of chapter 15)."""

from __future__ import annotations

import json
from collections.abc import Callable

import httpx
from pydantic import JsonValue

from discovery_ingest.browser.errors import BrowserAuthError, BrowserQuotaExceeded, BrowserRequestError

RATE_LIMIT_CODE = 2001
Scrub = Callable[[str], str]


def _errors(response: httpx.Response) -> list[dict[str, JsonValue]]:
    payload = _payload(response)
    errors = payload.get("errors") if payload else None
    return [item for item in errors if isinstance(item, dict)] if isinstance(errors, list) else []


def _payload(response: httpx.Response) -> dict[str, JsonValue] | None:
    try:
        payload = json.loads(response.content)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def retry_after(response: httpx.Response) -> float | None:
    """Return ``Retry-After`` in seconds, or ``None`` when absent or not a number."""
    try:
        return float(response.headers["retry-after"])
    except (KeyError, ValueError):
        return None


def is_rate_limited(response: httpx.Response, max_retry_after: float) -> bool:
    """Whether this is the short rate-limit ``429`` (code 2001) that one retry after the throttle can clear."""
    wait = retry_after(response)
    codes = [error.get("code") for error in _errors(response)]
    return response.status_code == 429 and RATE_LIMIT_CODE in codes and wait is not None and wait <= max_retry_after


def _describe(response: httpx.Response, scrub: Scrub) -> str:
    detail = "; ".join(f"code {error.get('code')}: {error.get('message')}" for error in _errors(response))
    return scrub(f"Cloudflare HTTP {response.status_code}" + (f" {detail}" if detail else ""))


def raise_for_response(response: httpx.Response, scrub: Scrub, ms_used: int | None = None) -> None:
    """Raise the browser error that ``response`` stands for, carrying ``ms_used``; return for a success."""
    status = response.status_code
    if status == 429:
        raise BrowserQuotaExceeded(_describe(response, scrub), retry_after(response), ms_used=ms_used)
    if status in (401, 403):
        raise BrowserAuthError(_describe(response, scrub), ms_used=ms_used)
    if status >= 400:
        raise BrowserRequestError(_describe(response, scrub), retryable=status >= 500, ms_used=ms_used)


def envelope(response: httpx.Response, ms_used: int | None = None) -> dict[str, JsonValue]:
    """Return the JSON envelope of a successful response, or raise a permanent :class:`BrowserRequestError`."""
    payload = _payload(response)
    if payload is None or payload.get("success") is not True:
        raise BrowserRequestError("Cloudflare answered 200 without a usable result", retryable=False, ms_used=ms_used)
    return payload
