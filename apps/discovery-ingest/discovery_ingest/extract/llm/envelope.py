"""Read the model's answer and token usage out of a successful ``/ai/run`` response.

Probe-dependent (chapter E4, Step 0): the default follows the documented envelope, ``result.response`` (an object in
JSON mode, a string for some models) and ``result.usage.prompt_tokens`` / ``completion_tokens`` and, when present, ``result.usage.neurons``. If the probe shows
another shape, change this module only.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass

import httpx
from pydantic import JsonValue

from discovery_ingest.extract.llm.classify import json_payload
from discovery_ingest.extract.llm.client import LlmResult
from discovery_ingest.extract.llm.errors import LlmInvalidOutput


def _result(response: httpx.Response) -> dict[str, JsonValue]:
    payload = json_payload(response)
    result = payload.get("result") if payload and payload.get("success") is True else None
    if not isinstance(result, dict):
        raise LlmInvalidOutput("Cloudflare answered 200 without a result")
    return result


def _answer_text(result: dict[str, JsonValue]) -> str:
    answer = result.get("response")
    if isinstance(answer, str):
        _require_json(answer)
        return answer
    if isinstance(answer, dict | list):
        return json.dumps(answer, ensure_ascii=False)
    raise LlmInvalidOutput("the model answer is missing from the response")


def _require_json(text: str) -> None:
    try:
        json.loads(text)
    except json.JSONDecodeError as err:
        raise LlmInvalidOutput("the model answer is not valid JSON") from err


@dataclass(frozen=True, slots=True)
class ReportedUsage:
    """What the provider said the call used; each part is ``None`` when it was absent or not believable."""

    input_tokens: int | None
    output_tokens: int | None
    neurons: float | None


def _usage_fields(result: dict[str, JsonValue]) -> dict[str, JsonValue]:
    usage = result.get("usage")
    return usage if isinstance(usage, dict) else {}


def token_count(value: JsonValue) -> int | None:
    """Return ``value`` as a token count when it is an integer (not a boolean), else ``None``."""
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def reported_neurons(value: JsonValue) -> float | None:
    """Return ``value`` as neurons when it is a finite non-negative number (probe 2026-10-28: ``usage.neurons``)."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value) if math.isfinite(value) and value >= 0 else None


def _tokens(fields: dict[str, JsonValue]) -> tuple[int | None, int | None]:
    prompt, completion = token_count(fields.get("prompt_tokens")), token_count(fields.get("completion_tokens"))
    return (prompt, completion) if prompt is not None and completion is not None else (None, None)


def read_usage(response: httpx.Response) -> ReportedUsage:
    """Return the usage of a 2xx ``response``, whether or not its answer is usable; raise when there is no result."""
    fields = _usage_fields(_result(response))
    return ReportedUsage(*_tokens(fields), reported_neurons(fields.get("neurons")))


def read_result(response: httpx.Response, model: str) -> LlmResult:
    """Return the :class:`LlmResult` of a 2xx ``response``, or raise :class:`LlmInvalidOutput`."""
    answer, usage = _answer_text(_result(response)), read_usage(response)
    return LlmResult(answer, usage.input_tokens, usage.output_tokens, model, usage.neurons)
