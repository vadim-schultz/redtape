"""CloudflareEmbeddingClient: request shape, parsing and error classification (chapter 1 of the search-first suite)."""

from __future__ import annotations

import json

import httpx
import pytest
from discovery_ingest.extract.llm.errors import LlmAuthError, LlmInvalidOutput, LlmQuotaExceeded, LlmRequestError

from embedding_transport import (
    ACCOUNT_ID,
    EMBED_MODEL,
    TOKEN,
    embedding_client,
    embedding_success,
    failure,
    vectors,
)

USAGE = {"prompt_tokens": 12, "total_tokens": 12}


def test_a_successful_response_gives_one_vector_per_text_in_order_with_the_dimension_from_the_response() -> None:
    """embedding client · parses a successful response."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return embedding_success(vectors(2, 4), {**USAGE, "neurons": 0.5})

    result = embedding_client(handler).embed(["Kindergeld", "Wohngeld"])

    request = seen[0]
    assert request.headers["authorization"] == f"Bearer {TOKEN}"
    assert request.url.path == f"/client/v4/accounts/{ACCOUNT_ID}/ai/run/{EMBED_MODEL}"
    assert json.loads(request.content) == {"text": ["Kindergeld", "Wohngeld"]}
    assert result.vectors == ((1.0,) * 4, (2.0,) * 4)
    assert (result.dimension, result.model, result.input_tokens, result.neurons) == (4, EMBED_MODEL, 12, 0.5)
    assert result.latency_ms >= 0


def test_a_requested_dimension_is_sent_as_the_dimensions_parameter() -> None:
    """embedding client · the Matryoshka ``dimensions`` parameter is sent only when asked for."""
    bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return embedding_success(vectors(1, 2))

    client = embedding_client(handler)
    client.embed(["a"])
    client.embed(["a"], dimensions=2)

    assert "dimensions" not in bodies[0] and bodies[1]["dimensions"] == 2


def test_missing_usage_gives_none_tokens_and_neurons_without_raising() -> None:
    """embedding client · no usage block means no token count and no neurons."""
    result = embedding_client(lambda _request: embedding_success(vectors(1, 3))).embed(["a"])

    assert (result.input_tokens, result.neurons) == (None, None)


@pytest.mark.parametrize("status", [401, 403])
def test_401_and_403_are_an_auth_error_without_the_token_in_the_text(status: int) -> None:
    """embedding client · maps 401 and 403 to an auth error and never repeats the token."""
    handler = lambda _request: failure(status, 10000, f"Authentication error {TOKEN} {ACCOUNT_ID}")  # noqa: E731

    with pytest.raises(LlmAuthError) as caught:
        embedding_client(handler).embed(["a"])

    assert TOKEN not in str(caught.value) and ACCOUNT_ID not in str(caught.value)


def test_429_with_the_allowance_code_is_a_quota_error() -> None:
    """embedding client · the daily allowance 429 (code 4006) is a quota error, not a retryable request error."""
    handler = lambda _request: failure(429, 4006, "you have used up your daily free allocation")  # noqa: E731

    with pytest.raises(LlmQuotaExceeded):
        embedding_client(handler).embed(["a"])


def test_a_rate_limit_429_and_a_5xx_are_retryable_and_a_400_is_not() -> None:
    """embedding client · the error taxonomy of the chat client applies unchanged."""
    retryable = [failure(429, 2001, "Rate limit exceeded"), failure(503, 3040, "unavailable")]
    for response in retryable:
        with pytest.raises(LlmRequestError) as caught:
            embedding_client(lambda _request, response=response: response).embed(["a"])  # type: ignore[misc]
        assert caught.value.retryable is True

    with pytest.raises(LlmRequestError) as rejected:
        embedding_client(lambda _request: failure(400, 5006, "too many inputs")).embed(["a"])
    assert rejected.value.retryable is False


def test_a_connection_error_is_a_retryable_request_error_without_the_token() -> None:
    """embedding client · a transport failure is retryable and scrubbed."""

    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"cannot reach host with {TOKEN}")

    with pytest.raises(LlmRequestError) as caught:
        embedding_client(handler).embed(["a"])

    assert caught.value.retryable is True and TOKEN not in str(caught.value)


def test_a_vector_count_that_differs_from_the_input_count_is_an_error() -> None:
    """embedding client · a response with a vector count that differs from the input count is an error."""
    with pytest.raises(LlmInvalidOutput, match="2 vectors for 3 texts"):
        embedding_client(lambda _request: embedding_success(vectors(2, 4))).embed(["a", "b", "c"])


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, json={"success": True, "result": {}}),
        httpx.Response(200, json={"success": False, "result": None}),
        httpx.Response(200, content=b"not json"),
        embedding_success([[1.0, 2.0], [1.0]]),
    ],
    ids=["no-data", "unsuccessful", "not-json", "ragged"],
)
def test_an_unreadable_or_ragged_answer_is_an_invalid_output_error(response: httpx.Response) -> None:
    """embedding client · a 200 without usable vectors is never silently accepted."""
    with pytest.raises(LlmInvalidOutput):
        embedding_client(lambda _request: response).embed(["a", "b"])


def test_no_texts_is_refused_before_any_request() -> None:
    """embedding client · an empty batch raises ValueError and sends nothing."""

    def handler(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("a request was sent")

    with pytest.raises(ValueError, match="no texts"):
        embedding_client(handler).embed([])
