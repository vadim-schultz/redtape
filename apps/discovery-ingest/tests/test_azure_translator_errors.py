"""Azure errors · status and code map onto the port's categories, and the key never appears in a message or a log line."""

from __future__ import annotations

import logging

import httpx
import pytest
from discovery_ingest.translation.errors import (
    PermanentError,
    QuotaExceeded,
    RateLimited,
    TransientError,
    TranslationEngineError,
    Unauthorised,
)

from azure_transport import KEY, FakeClock, engine, failure, faithful_answer
from translation_fakes import batch, unit

ONE_UNIT = batch(unit("a", "Antrag", "Gebühr"))


@pytest.mark.parametrize(
    ("status", "code", "category"),
    [
        (403, "403001", QuotaExceeded),
        (401, "401000", Unauthorised),
        (403, "403000", Unauthorised),
        (429, "429000", RateLimited),
        (429, "429001", RateLimited),
        (429, "429002", RateLimited),
        (429, "", RateLimited),
        (503, "500000", TransientError),
        (500, "500000", TransientError),
        (408, "408000", TransientError),
        (400, "400050", PermanentError),
        (400, "400000", PermanentError),
    ],
)
def test_status_and_code_map_to_the_port_category(
    status: int, code: str, category: type[TranslationEngineError]
) -> None:
    """Azure · 403001 maps to QuotaExceeded; 401000 to Unauthorised; 429000 and 503 to TransientError; 400050 to PermanentError."""
    adapter = engine(lambda _request: failure(status, code, "service said no"))

    with pytest.raises(category):
        adapter.translate(ONE_UNIT)


def test_a_429_maps_to_rate_limited_and_keeps_the_retry_after_seconds_the_service_sent() -> None:
    """Azure · a 429 maps to RateLimited with the Retry-After seconds of its header; the transport waits that long twice."""
    clock = FakeClock()
    adapter = engine(lambda _request: failure(429, "429000", "slow", {"Retry-After": "7"}), clock=clock)

    with pytest.raises(RateLimited) as raised:
        adapter.translate(ONE_UNIT)

    assert raised.value.retry_after == 7.0
    assert clock.slept == [7.0, 7.0]


def test_a_429_without_retry_after_leaves_retry_after_unset_and_waits_two_then_four_seconds() -> None:
    """Azure · a 429 with no Retry-After header leaves retry_after unset; the transport waits 2 s, then 4 s, then raises."""
    clock = FakeClock()
    calls: list[int] = []

    def handler(_request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return failure(429, "429001", "slow")

    with pytest.raises(RateLimited) as raised:
        engine(handler, clock=clock).translate(ONE_UNIT)

    assert raised.value.retry_after is None
    assert (len(calls), clock.slept) == (3, [2.0, 4.0])


def test_a_throttled_request_sent_again_after_its_retry_after_returns_the_answer() -> None:
    """Azure · a throttled request that succeeds on its second send returns its answer; only the first wait is spent."""
    clock = FakeClock()
    replies = [failure(429, "429000", "slow", {"Retry-After": "3"})]

    def handler(request: httpx.Request) -> httpx.Response:
        return replies.pop(0) if replies else faithful_answer(request)

    outcome = engine(handler, clock=clock).translate(ONE_UNIT)

    assert outcome.results[0].title == "[en] Antrag"
    assert clock.slept == [3.0]


def test_a_connection_failure_is_transient() -> None:
    """Azure · a timeout or a connection error is a transient failure, so the task may be retried later."""

    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out")

    with pytest.raises(TransientError, match="did not answer"):
        engine(handler).translate(ONE_UNIT)


def test_the_key_never_appears_in_an_error_message_or_a_log_line(caplog: pytest.LogCaptureFixture) -> None:
    """Azure · the key never appears in an error message or log line, even when the service echoes it back."""
    caplog.set_level(logging.DEBUG)
    echo = f"the key {KEY} is not valid for this resource"

    for status, code in ((401, "401000"), (403, "403001"), (429, "429000"), (400, "400050")):
        with pytest.raises(TranslationEngineError) as raised:
            engine(lambda _request, s=status, c=code: failure(s, c, echo)).translate(ONE_UNIT)
        assert KEY not in str(raised.value)
        assert KEY not in repr(raised.value)
        assert "[redacted]" in str(raised.value)

    assert KEY not in caplog.text


def test_an_error_body_that_is_not_json_is_still_mapped_by_its_status() -> None:
    """Azure · an error whose body is not the usual envelope is still mapped by its HTTP status."""

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, content=b"Service Unavailable")

    with pytest.raises(TransientError):
        engine(handler).translate(ONE_UNIT)
