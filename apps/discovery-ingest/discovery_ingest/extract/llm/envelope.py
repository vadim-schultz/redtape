"""Read the model's answer and token usage out of a successful ``/ai/run`` response.

Probe-dependent (chapter E4, Step 0): the default follows the documented envelope, ``result.response`` (an object in
JSON mode, a string for some models) and ``result.usage.prompt_tokens`` / ``completion_tokens``. If the probe shows
another shape, change this module only.
"""

from __future__ import annotations

import json

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


def _tokens(result: dict[str, JsonValue]) -> tuple[int | None, int | None]:
    usage = result.get("usage")
    fields = usage if isinstance(usage, dict) else {}
    prompt, completion = fields.get("prompt_tokens"), fields.get("completion_tokens")
    if isinstance(prompt, int) and isinstance(completion, int):
        return prompt, completion
    return None, None


def read_result(response: httpx.Response, model: str) -> LlmResult:
    """Return the :class:`LlmResult` of a 2xx ``response``, or raise :class:`LlmInvalidOutput`."""
    result = _result(response)
    return LlmResult(_answer_text(result), *_tokens(result), model)
