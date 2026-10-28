"""llm probe: a table per model, never the credentials, findings instead of crashes (chapter E4, loop C)."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from discovery_ingest.browser.throttle import Throttle
from discovery_ingest.cli import main
from discovery_ingest.extract.llm.probe import ProbeReport, run_probe
from discovery_ingest.extract.llm.probe_report import report_lines

from llm_transport import ACCOUNT_ID, MODEL, TOKEN, Handler, failure, settings, success

BIG_MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
FIXTURE = Path(__file__).parent / "fixtures" / "pages" / "table_page.html"
USAGE = {"prompt_tokens": 1000, "completion_tokens": 200, "total_tokens": 1200}
_REAL_HTTPX_CLIENT = httpx.Client
ANSWER = {
    "page_kind": "form",
    "domain_codes": ["housing"],
    "situation_codes": [],
    "documents": [
        {"name": "Personalausweis oder Reisepass", "role": "required", "quote": "Personalausweis oder Reisepass"},
        {"name": "Phantom", "role": "required", "quote": "this sentence is not on the page"},
    ],
    "dependencies": [],
}


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("DISCOVERY_API_URL", "DISCOVERY_API_KEY", "LLM_MODEL", "LLM_MAX_TOKENS"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", ACCOUNT_ID)
    monkeypatch.setenv("CLOUDFLARE_AI_API_TOKEN", TOKEN)
    monkeypatch.setattr("time.sleep", lambda _seconds: None)


def _markdown(status: int = 200) -> httpx.Response:
    if status != 200:
        return failure(status, 7000, "unsupported format html")
    entry = {
        "name": "table_page.html",
        "mimeType": "text/markdown",
        "format": "markdown",
        "tokens": "310",
        "data": "# x",
    }
    return httpx.Response(200, json={"success": True, "result": [entry]})


def _chat(content: str) -> httpx.Response:
    return httpx.Response(
        200, json={"choices": [{"message": {"role": "assistant", "content": content}}], "usage": USAGE}
    )


def _handler(**overrides: httpx.Response) -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        path, body = request.url.path, request.content
        if path.endswith("/ai/tomarkdown"):
            return overrides.get("markdown", _markdown())
        if path.endswith("/chat/completions"):
            return overrides.get("chat", _chat(json.dumps(ANSWER)))
        if b'"max_tokens": 16' in body or b'"max_tokens":16' in body:
            return overrides.get("violation", failure(400, 5024, f"JSON Mode couldn't be met {TOKEN}"))
        return overrides.get("run", success(ANSWER, USAGE))

    return handler


def _probe(handler: Handler, models: list[str], *, max_neurons: float = 10**6) -> ProbeReport:
    throttle = Throttle(1.0, clock=lambda: 0.0, sleep=lambda _seconds: None)
    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        html = FIXTURE.read_text()
        return run_probe(settings(), models, html, http=http, throttle=throttle, max_neurons=max_neurons)


def _text(report: ProbeReport) -> str:
    return "\n".join(report_lines(report, settings()))


def test_the_probe_prints_a_table_per_model_and_never_prints_the_token() -> None:
    """probe · one table per model with every item; the token and account id never appear, even in an echo."""
    text = _text(_probe(_handler(), [MODEL, BIG_MODEL]))

    assert f"model {MODEL}" in text and f"model {BIG_MODEL}" in text
    for item in ("envelope", "chat-envelope", "usage", "acceptance", "violation", "cost", "quality", "quota"):
        assert text.count(f"| {item} |") == 2, item
    assert "result.response=object" in text and "prompt_tokens=1000" in text and "completion_tokens=200" in text
    assert "grounded documents 1 of 2" in text
    assert "neurons=" in text and "wall_ms=" in text
    assert TOKEN not in text and ACCOUNT_ID not in text and "<redacted>" in text


def test_the_probe_exits_non_zero_when_settings_are_missing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """probe · a missing credential exits 2 and names only the variable."""
    monkeypatch.delenv("CLOUDFLARE_AI_API_TOKEN")

    code = main(["llm", "probe", "--model", MODEL, "--fixture", str(FIXTURE)])

    assert code == 2
    err = capsys.readouterr().err
    assert "CLOUDFLARE_AI_API_TOKEN" in err and ACCOUNT_ID not in err


def test_the_probe_reports_an_unsupported_response_format_as_a_finding_instead_of_crashing() -> None:
    """probe · a model that rejects response_format gets an acceptance finding; the next model is still probed."""
    rejected = failure(400, 5006, "response_format is not supported for this model")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith(f"/ai/run/{MODEL}") or request.url.path.endswith("/chat/completions"):
            return rejected
        return _handler()(request)

    report = _probe(handler, [MODEL, BIG_MODEL])
    text = _text(report)

    assert "does not accept response_format" in text and "HTTP 400 code 5006" in text
    assert f"model {BIG_MODEL}" in text and "grounded documents 1 of 2" in text
    assert report.refused is False


def test_the_probe_stops_at_a_rejected_token_and_the_cli_exits_one(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """probe · 401 stops the probe at once (one call, no second model) and the exit status is 1."""
    sent: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return failure(401, 10000, "Authentication error")

    report = _probe(handler, [MODEL, BIG_MODEL])
    assert report.refused is True and "401" in str(report.stopped)
    assert not any(request.url.path.endswith(f"/ai/run/{BIG_MODEL}") for request in sent)

    def client_factory(**kwargs: object) -> httpx.Client:
        kwargs["transport"] = httpx.MockTransport(handler)
        return _REAL_HTTPX_CLIENT(**kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr("discovery_ingest.extract.llm.probe_cli.httpx.Client", client_factory)
    assert main(["llm", "probe", "--model", MODEL, "--fixture", str(FIXTURE)]) == 1
    assert TOKEN not in capsys.readouterr().out


def test_the_cli_runs_with_only_the_two_cloudflare_variables(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """probe · exit 0 and a table with neither the Discovery API address nor its key set."""

    def client_factory(**kwargs: object) -> httpx.Client:
        kwargs["transport"] = httpx.MockTransport(_handler())
        return _REAL_HTTPX_CLIENT(**kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr("discovery_ingest.extract.llm.probe_cli.httpx.Client", client_factory)

    code = main(["llm", "probe", "--model", MODEL, "--fixture", str(FIXTURE)])

    assert code == 0 and "grounded documents 1 of 2" in capsys.readouterr().out


def test_the_cli_refuses_a_missing_fixture_or_no_model(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """probe · a fixture path that does not exist exits 2 before any call; so does a run without --model."""
    monkeypatch.setattr("discovery_ingest.extract.llm.probe_cli.httpx.Client", lambda **_kw: pytest.fail("called"))

    assert main(["llm", "probe", "--model", MODEL, "--fixture", str(tmp_path / "nope.html")]) == 2
    assert main(["llm", "probe", "--fixture", str(FIXTURE)]) == 2
    assert "fixture" in capsys.readouterr().err


def test_a_model_without_a_price_row_is_probed_and_flagged() -> None:
    """probe · an unknown model still runs (that is the point) and the cost row says the meter would refuse it."""
    text = _text(_probe(_handler(), ["@cf/acme/candidate-1b"]))

    assert "no price row" in text and "grounded documents 1 of 2" in text


def test_the_neuron_cap_stops_the_probe_before_the_next_model() -> None:
    """probe · once the spent neurons reach the cap no further model is called."""
    report = _probe(_handler(), [BIG_MODEL, MODEL], max_neurons=1)
    text = _text(report)

    assert f"model {BIG_MODEL}" in text and f"model {MODEL}" not in text
    assert report.stopped is not None and "neuron cap" in report.stopped


def test_a_markdown_conversion_is_compared_and_an_unsupported_one_is_a_finding() -> None:
    """probe · cleaner vs toMarkdown: characters and tokens when it works, 'not supported' when it does not."""
    works = _text(_probe(_handler(), [MODEL]))
    refused = _text(_probe(_handler(markdown=_markdown(400)), [MODEL]))

    assert "| cleaner |" in works and "toMarkdown 3 chars" in works and "tokens=310" in works
    assert "toMarkdown not supported" in refused and "HTTP 400" in refused


def test_a_natural_quota_error_is_recorded_with_its_classification() -> None:
    """probe · a daily-allowance error on a call lands in the quota row, classified, and stops the probe."""
    quota = failure(429, 4006, "you have used up your daily free allocation of 10,000 neurons")

    report = _probe(_handler(run=quota), [MODEL, BIG_MODEL])
    text = _text(report)

    assert "| quota |" in text and "LlmQuotaExceeded" in text and "HTTP 429 code 4006" in text
    assert report.refused is True and f"model {BIG_MODEL}" not in text
