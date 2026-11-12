"""translate probe --engine azure-translator: the per-locale report, the glossary recommendation, the spend cap and the fixture gate.

Every test runs on a fake transport. The guard fixture makes a real HTTP transport fail, so a test that reached the
network would fail rather than spend.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterator
from pathlib import Path

import httpx
import pytest
from discovery_ingest.cli import main
from discovery_ingest.translation.locale_codes import DEFAULT_TARGET_LOCALES
from discovery_ingest.translation.probe_azure import AzureProbePlan, connection_from_settings, run_azure_probe
from discovery_ingest.translation.probe_azure_report import AzureProbeReport, build_report
from discovery_ingest.translation.probe_azure_units import (
    PLURAL_UNITS,
    TOKEN_UNITS,
    ProbeFixtureError,
    load_units,
)
from discovery_ingest.translation.units import TranslationUnit

from azure_transport import ENDPOINT, KEY, REGION, connection, failure, inputs_in

Handler = Callable[[httpx.Request], httpx.Response]
Mangle = Callable[[str, str], str]
Meter = Callable[[list[dict[str, object]]], float | None]
LOCALES = ("tr", "ro")


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """A real transport must never be used: the probe is tested through fake transports only."""

    def refuse(self: httpx.HTTPTransport, request: httpx.Request) -> httpx.Response:
        raise AssertionError(f"the probe tried the network: {request.url}")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", refuse)
    yield


def _card(number: int, title: str | None = None) -> TranslationUnit:
    """A synthetic card: German text with a number, a date and a URL, and no glossary term unless ``title`` says so."""
    text = title or f"Hinweis {number} zur Frist"
    return TranslationUnit(
        f"card-{number}", text, f"Frist {number}: 12,{number} Euro bis 01.03.2025. Siehe https://example.test/{number}."
    )


def _units(count: int = 4) -> tuple[TranslationUnit, ...]:
    return tuple(_card(number) for number in range(1, count + 1))


def _keep(_target: str, text: str) -> str:
    return text


def _billed_as_sent(inputs: list[dict[str, object]]) -> float | None:
    return float(sum(len(str(item["text"])) for item in inputs))


def _service(mangle: Mangle = _keep, meter: Meter = _billed_as_sent) -> Handler:
    """A fake Azure: each input comes back as ``[target] text``, through ``mangle``, with the header ``meter`` gives."""

    def handler(request: httpx.Request) -> httpx.Response:
        inputs = inputs_in(request)
        answers = []
        for item in inputs:
            target = str(item["targets"][0]["language"])  # type: ignore[index]
            answers.append({"translations": [{"text": mangle(target, f"[{target}] {item['text']}"), "to": target}]})
        billed = meter(inputs)
        headers = {} if billed is None else {"X-metered-usage": str(billed)}
        return httpx.Response(200, json=answers, headers=headers)

    return handler


def _report(
    handler: Handler,
    units: tuple[TranslationUnit, ...] | None = None,
    *,
    locales: tuple[str, ...] = LOCALES,
    cap: float = 10_000.0,
) -> AzureProbeReport:
    http = httpx.Client(transport=httpx.MockTransport(handler))
    plan = AzureProbePlan(units or _units(), locales, cap, connection(), 0.0)
    return build_report(plan, run_azure_probe(plan, http))


def _drop_numbers_in(locale: str, count: int) -> Mangle:
    """Lose the number of the first ``count`` card titles, in ``locale`` only: each such title then fails the numbers check."""

    def mangle(target: str, text: str) -> str:
        if target != locale:
            return text
        for number in range(1, count + 1):
            text = text.replace(f"Hinweis {number} ", "Hinweis ")
        return text

    return mangle


def _by_locale(report: AzureProbeReport) -> dict[str, object]:
    return {row.locale: row for row in report.locales}


def test_the_report_gives_per_locale_valid_share_glossary_findings_placeholder_survival_and_billed_and_estimated_characters() -> (
    None
):
    """Probe · the report gives per-locale valid share, glossary findings, placeholder survival and billed and estimated characters."""
    units = (*_units(3), _card(4, "Antrag 4 zur Frist"))

    report = _report(_service(), units)

    assert [row.locale for row in report.locales] == list(LOCALES)
    for row in report.locales:
        assert (row.units, row.valid_units, row.valid_share) == (4, 3, 0.75)
        assert row.glossary_findings == 1 and row.placeholder_failures == 0
        assert (row.token_units, row.token_valid) == (len(TOKEN_UNITS), len(TOKEN_UNITS))
        assert (row.plural_units, row.plural_valid) == (len(PLURAL_UNITS), len(PLURAL_UNITS))
        assert row.billed_characters == row.estimated_characters > 0
    assert (
        report.billed_characters
        == report.estimated_characters
        >= sum(row.estimated_characters for row in report.locales)
    )


def test_a_protected_placeholder_the_service_drops_fails_the_token_case() -> None:
    """Probe · a chapter 04 token the service drops is not restored, so the token unit fails and is counted."""
    report = _report(_service(lambda _target, text: text.replace("⟦0⟧", "")))

    for row in report.locales:
        assert row.token_units == len(TOKEN_UNITS) and row.token_valid == 0


@pytest.mark.parametrize(("broken", "expected"), [(0, "strict"), (1, "strict"), (2, "advisory")])
def test_the_recommended_mode_is_strict_only_when_every_locale_reaches_ninety_percent_valid_units(
    broken: int, expected: str
) -> None:
    """Probe · the recommended mode is strict only when every locale reaches 90% valid units."""

    report = _report(_service(_drop_numbers_in("tr", broken)), _units(10), locales=("tr", "ro"))

    assert report.recommended_glossary_mode == expected


def test_a_locale_that_was_not_measured_counts_as_not_reaching_the_threshold() -> None:
    """Probe · a spend cap that ends the probe before a locale leaves that locale unmeasured and the mode advisory."""
    report = _report(_service(), _units(4), cap=5.0)

    assert report.stopped is not None and "max usage" in report.stopped
    assert report.billed_characters == 0
    assert all(not row.measured and row.valid_share == 0.0 for row in report.locales)
    assert report.recommended_glossary_mode == "advisory"


def test_the_probe_never_bills_past_the_spend_cap() -> None:
    """Probe · the probe reserves each call's characters before it sends it, so billed characters stay under the cap."""
    cap = 500.0

    report = _report(_service(), _units(3), cap=cap)

    assert report.stopped is not None and "max usage" in report.stopped
    assert 0 < report.billed_characters <= cap
    assert report.max_characters == cap


def test_billed_characters_come_from_the_metered_header_and_estimated_from_the_request() -> None:
    """Probe · billed is the sum of X-metered-usage and estimated the characters sent, per request."""

    def one_extra_per_input(inputs: list[dict[str, object]]) -> float | None:
        return _billed_as_sent(inputs) + len(inputs)

    row = _by_locale(_report(_service(meter=one_extra_per_input), _units(2), locales=("tr",)))["tr"]

    assert row.estimated_characters == sum(request.sent for request in row.requests)
    assert row.billed_characters == sum(request.metered or 0 for request in row.requests)
    assert row.billed_characters > row.estimated_characters
    assert row.unmetered_requests == 0


def test_a_request_without_the_metered_header_is_counted_as_unmetered() -> None:
    """Probe · a request whose answer has no X-metered-usage is counted as unmetered and bills nothing in the report."""
    row = _by_locale(_report(_service(meter=lambda _inputs: None), _units(2), locales=("tr",)))["tr"]

    assert row.requests and row.unmetered_requests == len(row.requests)
    assert row.billed_characters == 0 and row.estimated_characters > 0


def _html_meter(tags_billed: bool) -> Meter:
    """Bill HTML inputs with their tags (or without), and plain inputs as sent."""

    def meter(inputs: list[dict[str, object]]) -> float | None:
        total = 0.0
        for item in inputs:
            text = str(item["text"])
            visible = re.sub(r"<[^>]+>", "", text)
            total += len(text) if tags_billed or item.get("textType") != "html" else len(visible)
        return total

    return meter


@pytest.mark.parametrize("tags_billed", [True, False])
def test_the_markup_answer_says_whether_html_tags_are_billed(tags_billed: bool) -> None:
    """Probe · a small set of HTML inputs shows whether the service bills the tags (O2)."""
    report = _report(_service(meter=_html_meter(tags_billed)), _units(2), locales=("tr",))

    assert report.markup is not None
    assert report.markup.sent > report.markup.visible
    assert report.markup.tags_billed is tags_billed


def _throttled(inputs: list[dict[str, object]]) -> bool:
    """The throttle case sends one plain text; a fake that refuses only that shape answers 429 to it alone."""
    return len(inputs) == 1 and inputs[0].get("textType") == "plain"


def test_throttling_is_reported_per_attempt_with_the_service_code() -> None:
    """Probe · one call is repeated at the minimum interval; each attempt records its answer, a 429 with its code."""

    def answer(request: httpx.Request) -> httpx.Response:
        if _throttled(inputs_in(request)):
            return failure(429, "429001", "Rate limit is exceeded")
        return _service()(request)

    report = _report(answer, _units(2), locales=("tr",))

    assert report.throttle is not None
    assert report.throttle.attempts >= 2 and report.throttle.answered == 0
    assert report.throttle.throttled == report.throttle.attempts
    assert "HTTP 429 (429001)" in report.throttle.answers[0]


def test_a_fixture_that_is_missing_names_the_file(tmp_path: Path) -> None:
    """Probe · the probe refuses to run when the fixture file is missing, with a message naming the file."""
    missing = tmp_path / "azure_probe_units.json"

    with pytest.raises(ProbeFixtureError, match="azure_probe_units.json is missing"):
        load_units(missing)


@pytest.mark.parametrize("text", ["[]", "not json"])
def test_a_fixture_that_is_empty_or_not_units_names_the_file(tmp_path: Path, text: str) -> None:
    """Probe · an empty or malformed fixture is refused with a message naming the file."""
    path = tmp_path / "azure_probe_units.json"
    path.write_text(text, encoding="utf-8")

    with pytest.raises(ProbeFixtureError, match="azure_probe_units.json"):
        load_units(path)


def test_a_fixture_of_units_loads_as_translation_units(tmp_path: Path) -> None:
    """Probe · the fixture is a JSON list of key, title and description, read as translation units."""
    path = tmp_path / "azure_probe_units.json"
    path.write_text(json.dumps([{"key": "k1", "title": "Titel", "description": "Text"}]), encoding="utf-8")

    assert load_units(path) == (TranslationUnit("k1", "Titel", "Text"),)


def test_no_key_stops_before_any_http_call_with_a_message_naming_the_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Probe · no key stops before any HTTP call, with a message naming the variable."""
    monkeypatch.delenv("AZURE_TRANSLATOR_KEY", raising=False)
    monkeypatch.setenv("AZURE_TRANSLATOR_REGION", REGION)

    with pytest.raises(ValueError, match="AZURE_TRANSLATOR_KEY") as raised:
        connection_from_settings()

    assert KEY not in str(raised.value)


@pytest.fixture
def cli_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Credentials, a fixture of synthetic units in a temporary folder, and a fake transport for the command's client."""
    monkeypatch.setenv("AZURE_TRANSLATOR_KEY", KEY)
    monkeypatch.setenv("AZURE_TRANSLATOR_REGION", REGION)
    monkeypatch.setenv("AZURE_TRANSLATOR_ENDPOINT", ENDPOINT)
    monkeypatch.setattr("discovery_ingest.operations.translate_probe.AZURE_PROBE_MIN_INTERVAL_SECONDS", 0.0)
    real_client = httpx.Client
    service = _service()
    monkeypatch.setattr(
        "discovery_ingest.operations.translate_probe.httpx.Client",
        lambda **kwargs: real_client(**{**kwargs, "transport": httpx.MockTransport(service)}),
    )
    path = tmp_path / "azure_probe_units.json"
    path.write_text(
        json.dumps([{"key": f"k{n}", "title": f"Hinweis {n}", "description": f"Frist {n}"} for n in range(3)])
    )
    return path


def test_the_cli_probes_every_target_locale_by_default_and_writes_the_report_file(
    cli_environment: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Probe · translate probe --engine azure-translator covers every target locale, prints the JSON and writes --report."""
    report_path = tmp_path / "report.json"

    code = main(
        [
            "translate",
            "probe",
            "--engine",
            "azure-translator",
            "--units",
            str(cli_environment),
            "--report",
            str(report_path),
        ]
    )

    out = capsys.readouterr().out
    report = json.loads(out)
    assert code == 0 and report["stopped"] is None
    assert [row["locale"] for row in report["locales"]] == list(DEFAULT_TARGET_LOCALES)
    assert report["max_characters"] == 10_000.0 and report["engine"] == "azure-translator"
    assert json.loads(report_path.read_text(encoding="utf-8")) == report


def test_the_cli_refuses_when_the_default_fixture_is_missing_and_names_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Probe · without --units the probe reads tests/fixtures/azure_probe_units.json; when it is missing the command exits 2 naming it."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AZURE_TRANSLATOR_KEY", KEY)
    monkeypatch.setenv("AZURE_TRANSLATOR_REGION", REGION)

    assert main(["translate", "probe", "--engine", "azure-translator"]) == 2
    assert "tests/fixtures/azure_probe_units.json" in capsys.readouterr().err


def test_the_cli_names_the_key_variable_and_sends_nothing_when_the_key_is_unset(
    cli_environment: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Probe · the command exits 2 naming AZURE_TRANSLATOR_KEY, without a request, when the key is unset."""
    monkeypatch.delenv("AZURE_TRANSLATOR_KEY")

    assert main(["translate", "probe", "--engine", "azure-translator", "--units", str(cli_environment)]) == 2
    err = capsys.readouterr().err
    assert "AZURE_TRANSLATOR_KEY" in err and KEY not in err
