"""CloudflareAiClient: request shape, envelope, usage and error classification (chapter E4, loop A)."""

from __future__ import annotations

import json
import logging

import httpx
import pytest
from discovery_ingest.extract.llm.cloudflare import CloudflareAiClient
from discovery_ingest.extract.llm.errors import (
    LlmAuthError,
    LlmError,
    LlmInvalidOutput,
    LlmQuotaExceeded,
    LlmRequestError,
)

from llm_transport import ACCOUNT_ID, MESSAGES, MODEL, SCHEMA, TOKEN, client, failure, settings, success

USAGE = {"prompt_tokens": 1200, "completion_tokens": 340, "total_tokens": 1540}


def test_extract_posts_messages_schema_and_max_tokens_with_the_token_and_returns_text_and_usage() -> None:
    """extract · posts to the model's run endpoint with the bearer token and returns the json text and usage."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return success({"page_kind": "service"}, USAGE)

    result = client(handler).extract(MESSAGES, SCHEMA, max_tokens=900)

    request, body = seen[0], json.loads(seen[0].content)
    assert request.headers["authorization"] == f"Bearer {TOKEN}"
    assert request.url.path == f"/client/v4/accounts/{ACCOUNT_ID}/ai/run/{MODEL}"
    assert body == {
        "messages": MESSAGES,
        "response_format": {"type": "json_schema", "json_schema": SCHEMA},
        "max_tokens": 900,
    }
    assert json.loads(result.parsed_json) == {"page_kind": "service"}
    assert (result.input_tokens, result.output_tokens, result.model) == (1200, 340, MODEL)


def test_a_string_response_is_returned_as_it_came() -> None:
    """extract · models that answer with a json string keep that text."""
    text = '{"page_kind": "form"}'

    result = client(lambda _request: success(text, USAGE)).extract(MESSAGES, SCHEMA, max_tokens=900)

    assert result.parsed_json == text


def test_a_missing_usage_block_gives_none_tokens_without_raising() -> None:
    """extract · no usage block means no token counts; a partial block counts as missing."""
    absent = client(lambda _request: success({"page_kind": "other"})).extract(MESSAGES, SCHEMA, max_tokens=9)
    partial = client(lambda _request: success({"a": 1}, {"prompt_tokens": 5})).extract(MESSAGES, SCHEMA, max_tokens=9)

    assert (absent.input_tokens, absent.output_tokens) == (None, None)
    assert (partial.input_tokens, partial.output_tokens) == (None, None)


def test_the_neurons_reported_in_the_usage_block_are_carried_on_the_result() -> None:
    """extract · ``result.usage.neurons`` (probe 2026-10-28: 160.1 for one page) is kept next to the token counts."""
    usage = {**USAGE, "neurons": 160.1465301513672}

    result = client(lambda _request: success({"page_kind": "service"}, usage)).extract(MESSAGES, SCHEMA, max_tokens=900)

    assert result.neurons == pytest.approx(160.1465301513672)


@pytest.mark.parametrize("reported", [None, -1.0, "160", True])
def test_a_missing_or_unbelievable_neuron_figure_is_none(reported: object) -> None:
    """extract · absent, negative, non-numeric or boolean neurons give ``None`` so the price table decides."""
    usage: dict[str, object] = {**USAGE}
    if reported is not None:
        usage["neurons"] = reported

    result = client(lambda _request: success({"page_kind": "other"}, usage)).extract(MESSAGES, SCHEMA, max_tokens=9)  # type: ignore[arg-type]

    assert result.neurons is None


def test_an_infinite_neuron_figure_in_the_raw_body_is_none() -> None:
    """extract · ``Infinity`` is not valid JSON but Python reads it, so the figure is checked for being finite."""
    body = b'{"success": true, "result": {"response": {"a": 1}, "usage": {"prompt_tokens": 5, "completion_tokens": 6, "neurons": Infinity}}}'

    result = client(lambda _request: httpx.Response(200, content=body)).extract(MESSAGES, SCHEMA, max_tokens=9)

    assert (result.input_tokens, result.neurons) == (5, None)


@pytest.mark.parametrize(
    "answer",
    [
        httpx.Response(200, text="<html>gateway</html>"),
        httpx.Response(200, json={"success": True, "result": {}}),
        httpx.Response(200, json={"success": False, "errors": [], "result": None}),
        success("this is not json"),
    ],
)
def test_an_unusable_200_raises_invalid_output(answer: httpx.Response) -> None:
    """extract · a body without a json answer is LlmInvalidOutput, never a returned result."""
    with pytest.raises(LlmInvalidOutput):
        client(lambda _request: answer).extract(MESSAGES, SCHEMA, max_tokens=9)


def test_the_daily_allowance_error_raises_quota_exceeded() -> None:
    """extract · the daily neuron allowance error (429, code 4006) is LlmQuotaExceeded."""
    answer = failure(429, 4006, "you have used up your daily free allocation of 10,000 neurons")

    with pytest.raises(LlmQuotaExceeded):
        client(lambda _request: answer).extract(MESSAGES, SCHEMA, max_tokens=9)


def test_a_429_without_the_quota_code_is_a_retryable_request_error() -> None:
    """extract · a plain rate limit is not the quota: the task is retried, the day is not marked exhausted."""
    answer = failure(429, 3040, "Capacity temporarily exceeded", {"Retry-After": "3"})

    with pytest.raises(LlmRequestError) as raised:
        client(lambda _request: answer).extract(MESSAGES, SCHEMA, max_tokens=9)

    assert raised.value.retryable is True


@pytest.mark.parametrize("status", [401, 403])
def test_401_and_403_raise_auth_error(status: int) -> None:
    """extract · a rejected token or account is infrastructure, not the page."""
    with pytest.raises(LlmAuthError):
        client(lambda _request: failure(status, 10000, "Authentication error")).extract(MESSAGES, SCHEMA, max_tokens=9)


def test_the_invalid_json_error_raises_invalid_output() -> None:
    """extract · JSON Mode couldn't be met is LlmInvalidOutput whatever the status."""
    for status in (400, 422, 500):
        answer = failure(status, 5024, "JSON Mode couldn't be met")
        with pytest.raises(LlmInvalidOutput):
            client(lambda _request, answer=answer: answer).extract(MESSAGES, SCHEMA, max_tokens=9)


@pytest.mark.parametrize("status", [500, 502, 503])
def test_server_errors_are_retryable(status: int) -> None:
    """extract · a 5xx is a retryable task failure."""
    with pytest.raises(LlmRequestError) as raised:
        client(lambda _request: failure(status, 1000, "internal")).extract(MESSAGES, SCHEMA, max_tokens=9)

    assert raised.value.retryable is True


@pytest.mark.parametrize("error", [httpx.ReadTimeout("slow"), httpx.ConnectError("no route")])
def test_timeouts_and_connection_errors_are_retryable(error: httpx.HTTPError) -> None:
    """extract · a timeout or a refused connection is retryable."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise error

    with pytest.raises(LlmRequestError) as raised:
        client(handler).extract(MESSAGES, SCHEMA, max_tokens=9)

    assert raised.value.retryable is True


@pytest.mark.parametrize("status", [400, 404, 413, 422])
def test_other_client_errors_are_permanent(status: int) -> None:
    """extract · any other 4xx fails the task for good."""
    with pytest.raises(LlmRequestError) as raised:
        client(lambda _request: failure(status, 7000, "bad request")).extract(MESSAGES, SCHEMA, max_tokens=9)

    assert raised.value.retryable is False


def test_the_token_never_appears_in_an_exception_message_or_log_line(caplog: pytest.LogCaptureFixture) -> None:
    """extract · errors that echo the token or account id are scrubbed; nothing is logged with the token."""
    caplog.set_level(logging.DEBUG)
    leaks = [
        failure(400, 7000, f"bad {TOKEN} for {ACCOUNT_ID}"),
        failure(401, 10000, f"denied {TOKEN}"),
        failure(429, 4006, f"daily free allocation {TOKEN}"),
        failure(500, 1000, f"boom {TOKEN}"),
    ]
    messages: list[str] = []
    for answer in leaks:
        with pytest.raises(LlmError) as raised:
            client(lambda _request, answer=answer: answer).extract(MESSAGES, SCHEMA, max_tokens=9)
        messages.append(str(raised.value))

    def broken(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"cannot reach {request.url} with {TOKEN}", request=request)

    with pytest.raises(LlmError) as raised:
        client(broken).extract(MESSAGES, SCHEMA, max_tokens=9)
    messages.append(str(raised.value))

    assert all(TOKEN not in text and ACCOUNT_ID not in text for text in messages)
    assert TOKEN not in caplog.text and "<redacted>" in messages[-1]


def test_calls_are_spaced_by_the_throttle_and_a_model_is_required() -> None:
    """extract · every call enters the throttle; a client with an empty LLM_MODEL and no model refuses to start."""
    sleeps: list[float] = []
    subject = client(lambda _request: success({"a": 1}), sleeps=sleeps)

    subject.extract(MESSAGES, SCHEMA, max_tokens=9)
    subject.extract(MESSAGES, SCHEMA, max_tokens=9)

    assert sleeps == [1.0]
    with pytest.raises(ValueError, match="model"):
        CloudflareAiClient(settings(LLM_MODEL=""), model=None)
