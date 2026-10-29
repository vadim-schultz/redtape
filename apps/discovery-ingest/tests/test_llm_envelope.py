"""Recorded Workers AI response shapes of the two candidate models (chapter E17, loop B)."""

from __future__ import annotations

import json

import httpx
import pytest
from discovery_ingest.extract.llm.envelope import read_result
from discovery_ingest.extract.llm.errors import LlmInvalidOutput

MISTRAL = "@cf/mistralai/mistral-small-3.1-24b-instruct"
SCOUT = "@cf/meta/llama-4-scout-17b-16e-instruct"
ANSWER = {"page_kind": "service", "documents": []}
# Probe 2026-10-28: result carries these keys besides `response` and `usage`; usage adds `prompt_tokens_details`.
EXTRA_KEYS = {
    MISTRAL: ["choices", "created", "id", "kv_transfer_params", "model", "object", "prompt_logprobs", "tool_calls"],
    SCOUT: [
        "choices",
        "created",
        "ec_transfer_params",
        "id",
        "metrics",
        "model",
        "object",
        "prompt_text",
        "tool_calls",
    ],
}
USAGE = {
    MISTRAL: {"prompt_tokens": 2351, "completion_tokens": 602, "total_tokens": 2953, "neurons": 105.33425903320312},
    SCOUT: {"prompt_tokens": 2139, "completion_tokens": 582, "total_tokens": 2721, "neurons": 97.47545623779297},
}


def recorded(model: str, answer: object) -> httpx.Response:
    """A 200 envelope shaped like the probe's, with ``answer`` as ``result.response``."""
    usage = {**USAGE[model], "prompt_tokens_details": {"cached_tokens": 0}}
    result = {key: None for key in EXTRA_KEYS[model]} | {"response": answer, "usage": usage}
    return httpx.Response(200, json={"result": result, "success": True, "errors": [], "messages": []})


@pytest.mark.parametrize("model", [MISTRAL, SCOUT])
def test_a_recorded_object_answer_parses_with_its_tokens_and_reported_neurons(model: str) -> None:
    """read_result · the object answer, the token counts and usage.neurons come out as one LlmResult."""
    result = read_result(recorded(model, ANSWER), model)

    assert json.loads(result.parsed_json) == ANSWER
    assert (result.input_tokens, result.output_tokens) == (
        USAGE[model]["prompt_tokens"],
        USAGE[model]["completion_tokens"],
    )
    assert (result.neurons, result.model) == (USAGE[model]["neurons"], model)


@pytest.mark.parametrize("model", [MISTRAL, SCOUT])
def test_a_string_answer_parses_to_the_same_json(model: str) -> None:
    """read_result · the answer as a JSON string gives the same document as the object form."""
    as_string = read_result(recorded(model, json.dumps(ANSWER)), model)

    assert json.loads(as_string.parsed_json) == ANSWER
    assert as_string.neurons == USAGE[model]["neurons"]


@pytest.mark.parametrize("model", [MISTRAL, SCOUT])
def test_a_string_answer_that_is_not_json_is_invalid_output(model: str) -> None:
    """read_result · truncated text raises LlmInvalidOutput rather than returning it."""
    with pytest.raises(LlmInvalidOutput, match="not valid JSON"):
        read_result(recorded(model, '{"page_kind": "serv'), model)
