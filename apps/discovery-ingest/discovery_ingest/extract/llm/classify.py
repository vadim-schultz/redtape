"""Turn a Workers AI response into a result or one of the typed errors (the error table of chapter E4)."""

from __future__ import annotations

import json
from collections.abc import Callable

import httpx
from pydantic import JsonValue

from discovery_ingest.extract.llm.errors import (
    LlmAuthError,
    LlmError,
    LlmInvalidOutput,
    LlmQuotaExceeded,
    LlmRequestError,
)
from discovery_ingest.extract.llm.matchers import ErrorInfo, is_json_mode_failure, is_quota_error

Scrub = Callable[[str], str]
BODY_EXCERPT = 200


def json_payload(response: httpx.Response) -> dict[str, JsonValue] | None:
    """Return the body as a JSON object, or ``None`` when it is not one."""
    try:
        payload = json.loads(response.content)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _errors(payload: dict[str, JsonValue] | None) -> list[dict[str, JsonValue]]:
    errors = payload.get("errors") if payload else None
    return [item for item in errors if isinstance(item, dict)] if isinstance(errors, list) else []


def error_info(response: httpx.Response) -> ErrorInfo:
    """Read the status, error codes and message text of an error response."""
    errors = _errors(json_payload(response))
    codes = frozenset(code for error in errors if isinstance(code := error.get("code"), int))
    text = " ".join(str(error.get("message", "")) for error in errors) or response.text[:BODY_EXCERPT]
    return ErrorInfo(response.status_code, codes, text.lower())


def describe(response: httpx.Response, scrub: Scrub) -> str:
    errors = _errors(json_payload(response))
    detail = "; ".join(f"code {error.get('code')}: {error.get('message')}" for error in errors)
    return scrub(f"Cloudflare HTTP {response.status_code}" + (f" {detail}" if detail else ""))


def _is_auth_failure(info: ErrorInfo) -> bool:
    return info.status in (401, 403)


_FIXED_ERRORS: tuple[tuple[Callable[[ErrorInfo], bool], type[LlmError]], ...] = (
    (is_quota_error, LlmQuotaExceeded),
    (_is_auth_failure, LlmAuthError),
    (is_json_mode_failure, LlmInvalidOutput),
)
"""Checked in order: the quota error is a 429 too, and a JSON-mode failure can arrive under any 4xx or 5xx."""


def error_for(response: httpx.Response, scrub: Scrub) -> LlmError:
    """Return the typed error that the error ``response`` stands for."""
    info, message = error_info(response), describe(response, scrub)
    for matches, error_type in _FIXED_ERRORS:
        if matches(info):
            return error_type(message)
    return LlmRequestError(message, retryable=info.status == 429 or info.status >= 500)
