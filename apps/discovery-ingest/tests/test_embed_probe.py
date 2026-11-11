"""embed probe: dimension, reduced dimensions, batch limit, latency, tokens and neurons (chapter 1 of search-first)."""

from __future__ import annotations

import json

import httpx
import pytest
from discovery_ingest.cli import main
from discovery_ingest.extract.embedding.probe import REDUCED_DIMENSIONS, run_embed_probe

from embedding_transport import (
    ACCOUNT_ID,
    EMBED_MODEL,
    TOKEN,
    embedding_client,
    embedding_success,
    failure,
    texts_of,
    vectors,
)

NATIVE = 1024
BATCH_LIMIT = 64
USAGE = {"prompt_tokens": 10, "total_tokens": 10}


def _handler(*, native: int = NATIVE, batch_limit: int = BATCH_LIMIT, honours_dimensions: bool = True):  # noqa: ANN202
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if len(body["text"]) > batch_limit:
            return failure(400, 5006, f"too many inputs {TOKEN}")
        asked = body.get("dimensions")
        if asked is not None and asked > native:
            return failure(400, 5006, "dimensions out of range")
        dimension = asked if asked and honours_dimensions else native
        return embedding_success(vectors(len(body["text"]), dimension), USAGE)

    return handler


def test_the_probe_reports_dimension_batch_limit_tokens_and_neurons() -> None:
    """embed probe · reports dimension, batch limit and neurons from a canned response sequence."""
    report = run_embed_probe(embedding_client(_handler()), EMBED_MODEL)

    assert report.model == EMBED_MODEL and report.stopped is None
    assert report.dimension == NATIVE
    assert report.accepted_dimensions == [dim for dim in REDUCED_DIMENSIONS if dim < NATIVE]
    assert (report.largest_accepted_batch, report.first_rejected_batch) == (64, 100)
    assert report.latency_ms is not None and report.tokens > 0
    assert report.neurons > 0 and report.neurons_per_1k_tokens is not None


def test_a_server_that_ignores_the_dimensions_parameter_is_reported_as_not_accepting_it() -> None:
    """embed probe · a reduced dimension counts as accepted only when the returned vectors have that length."""
    report = run_embed_probe(embedding_client(_handler(honours_dimensions=False)), EMBED_MODEL)

    assert report.accepted_dimensions == []
    assert {check.returned for check in report.dimension_checks} == {NATIVE}


def test_the_probe_stops_at_the_first_rejected_batch_size_and_reports_the_last_good_one() -> None:
    """embed probe · stops at the first rejected batch size and reports the last good one."""
    sizes: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sizes.append(len(texts_of(request)))
        return _handler(batch_limit=16)(request)

    report = run_embed_probe(embedding_client(handler), EMBED_MODEL)

    assert (report.largest_accepted_batch, report.first_rejected_batch) == (16, 32)
    assert max(sizes) == 32 and sizes.count(32) == 1


def test_the_reported_neurons_win_over_the_estimate() -> None:
    """embed probe · neurons come from the usage block when it has them, from the price table otherwise."""

    calls: list[int] = []

    def reported(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return embedding_success(vectors(len(texts_of(request)), 8), {**USAGE, "neurons": 2.0})

    with_reported = run_embed_probe(embedding_client(reported), EMBED_MODEL)
    estimated = run_embed_probe(embedding_client(_handler()), EMBED_MODEL)

    assert with_reported.neurons == pytest.approx(2.0 * len(calls))
    assert estimated.neurons == pytest.approx(estimated.tokens * 1075 / 1e6)


@pytest.mark.parametrize(
    ("response", "reason"),
    [
        (failure(401, 10000, "Authentication error"), "LlmAuthError"),
        (failure(429, 4006, "you have used up your daily free allocation"), "LlmQuotaExceeded"),
        (failure(503, 3040, "unavailable"), "LlmRequestError"),
    ],
)
def test_an_auth_quota_or_transient_error_stops_the_probe_and_is_not_read_as_a_limit(
    response: httpx.Response, reason: str
) -> None:
    """embed probe · only a plain rejection is a finding; anything else stops the probe with a reason."""
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return response

    report = run_embed_probe(embedding_client(handler), EMBED_MODEL)

    assert report.stopped is not None and reason in report.stopped
    assert len(calls) == 1 and report.dimension is None and report.largest_accepted_batch is None


@pytest.fixture(autouse=True)
def _no_throttle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("discovery_ingest.operations.embed_probe.EMBED_MIN_INTERVAL_SECONDS", 0.0)


def test_the_cli_prints_one_json_report_and_never_the_token(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """embed probe · the command prints one JSON object, exit 0, with neither the token nor the account id."""
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", ACCOUNT_ID)
    monkeypatch.setenv("CLOUDFLARE_AI_API_TOKEN", TOKEN)
    real_client = httpx.Client
    monkeypatch.setattr(
        "discovery_ingest.operations.embed_probe.httpx.Client",
        lambda **kw: real_client(**{**kw, "transport": httpx.MockTransport(_handler())}),
    )

    code = main(["embed", "probe"])

    out = capsys.readouterr().out
    assert code == 0 and json.loads(out)["dimension"] == NATIVE
    assert TOKEN not in out and ACCOUNT_ID not in out


def test_the_cli_exits_2_naming_the_missing_variable_when_credentials_are_absent(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """embed probe · a missing credential exits 2 before any request and names only the variable."""
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", ACCOUNT_ID)
    monkeypatch.delenv("CLOUDFLARE_AI_API_TOKEN", raising=False)
    monkeypatch.setattr("discovery_ingest.operations.embed_probe.httpx.Client", lambda **_kw: pytest.fail("called"))

    assert main(["embed", "probe"]) == 2
    assert "CLOUDFLARE_AI_API_TOKEN" in capsys.readouterr().err


def test_the_cli_exits_1_when_the_probe_stopped(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """embed probe · a rejected token still prints the report, scrubbed, and exits 1."""
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", ACCOUNT_ID)
    monkeypatch.setenv("CLOUDFLARE_AI_API_TOKEN", TOKEN)
    real_client = httpx.Client
    denied = httpx.MockTransport(lambda _request: failure(401, 10000, f"Authentication error {TOKEN}"))
    monkeypatch.setattr(
        "discovery_ingest.operations.embed_probe.httpx.Client", lambda **kw: real_client(**{**kw, "transport": denied})
    )

    code = main(["embed", "probe"])

    out = capsys.readouterr().out
    assert code == 1 and "LlmAuthError" in json.loads(out)["stopped"] and TOKEN not in out
