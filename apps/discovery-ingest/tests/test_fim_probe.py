"""fim probe: status and top-level keys per steckbrief key, never the body (chapter 12)."""

from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest
from discovery_ingest.cli import main
from discovery_ingest.fim.probe import probe_keys, probe_lines
from discovery_ingest.worker.fetcher import PoliteUrlFetcher

Handler = Callable[[httpx.Request], httpx.Response]

BASE_URL = "https://fimportal.de"
OK_KEY = "99154021000000"
MISSING_KEY = "99070016261000"
SLOW_KEY = "99096049001001"
SECRET = "BODY-TEXT-THAT-MUST-NOT-BE-PRINTED"
_REAL_HTTPX_CLIENT = httpx.Client


def _fetcher(handler: Handler) -> PoliteUrlFetcher:
    def routed(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return handler(request)

    client = httpx.Client(transport=httpx.MockTransport(routed))
    return PoliteUrlFetcher(min_interval_per_host_s=0, http_client=client)


def _steckbrief(key: str) -> httpx.Response:
    return httpx.Response(200, json={"leistungsschluessel": key, "titel": SECRET, "kurztext": SECRET})


def _mixed(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith(OK_KEY):
        return _steckbrief(OK_KEY)
    if request.url.path.endswith(MISSING_KEY):
        return httpx.Response(404, text="not found")
    raise httpx.ReadTimeout("timed out", request=request)


def test_probe_prints_status_and_top_level_keys_without_the_body() -> None:
    """probe · prints status and top-level keys without the body."""
    results = probe_keys(_fetcher(lambda request: _steckbrief(OK_KEY)), BASE_URL, [OK_KEY])

    lines = probe_lines(results)

    assert lines[0] == f"{OK_KEY} status=200 keys=leistungsschluessel,titel,kurztext"
    assert lines[-1] == "gate: 1/1 returned 200 with leistungsschluessel (passed)"
    assert SECRET not in "\n".join(lines)


def test_probe_reports_a_404_and_a_timeout_per_key_without_aborting() -> None:
    """probe · reports a 404 and a timeout per key without aborting."""
    keys = [MISSING_KEY, SLOW_KEY, OK_KEY]

    lines = probe_lines(probe_keys(_fetcher(_mixed), BASE_URL, keys))

    assert lines[0] == f"{MISSING_KEY} status=404"
    assert lines[1].startswith(f"{SLOW_KEY} no response: timeout")
    assert lines[2].startswith(f"{OK_KEY} status=200")
    assert lines[-1] == "gate: 1/3 returned 200 with leistungsschluessel (failed)"


@pytest.mark.parametrize("body", [b"<html>nope</html>", b'["a", "b"]', b"\xff\xfe"])
def test_probe_guards_a_200_body_that_is_not_a_json_object(body: bytes) -> None:
    """probe · guards a 200 body that is not a json object."""
    lines = probe_lines(probe_keys(_fetcher(lambda request: httpx.Response(200, content=body)), BASE_URL, [OK_KEY]))

    assert lines[0] == f"{OK_KEY} status=200 body is not a JSON object"
    assert lines[-1].endswith("(failed)")


def test_probe_gate_passes_with_four_of_five_confirmed_keys() -> None:
    """probe · gate passes with four of five confirmed keys and fails with three."""
    keys = [f"9915402100000{n}" for n in range(5)]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith(keys[-1]):
            return httpx.Response(404)
        return _steckbrief(request.url.path.rsplit("/", 1)[-1])

    passed = probe_lines(probe_keys(_fetcher(handler), BASE_URL, keys))[-1]
    failed = probe_lines(probe_keys(_fetcher(handler), BASE_URL, [*keys[:3], keys[4], keys[4]]))[-1]

    assert passed == "gate: 4/5 returned 200 with leistungsschluessel (passed)"
    assert failed == "gate: 3/5 returned 200 with leistungsschluessel (failed)"


def _patch_network(monkeypatch: pytest.MonkeyPatch, handler: Handler) -> None:
    def routed(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404) if request.url.path == "/robots.txt" else handler(request)

    def client_factory(**kwargs: object) -> httpx.Client:
        kwargs["transport"] = httpx.MockTransport(routed)
        return _REAL_HTTPX_CLIENT(**kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr("discovery_ingest.worker.fetcher.httpx.Client", client_factory)
    monkeypatch.setattr("discovery_ingest.worker.pacing.time.sleep", lambda _seconds: None)


def test_probe_cli_prints_one_line_per_key_and_exits_zero_when_the_gate_passes(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """fim probe CLI · prints one line per key and exits 0 when the gate passes."""
    _patch_network(monkeypatch, lambda request: _steckbrief(OK_KEY))

    exit_code = main(["fim", "probe", "--keys", f" {OK_KEY} ,{OK_KEY}"])

    out = capsys.readouterr().out.splitlines()
    assert exit_code == 0
    assert out[:2] == [f"{OK_KEY} status=200 keys=leistungsschluessel,titel,kurztext"] * 2
    assert out[-1].endswith("(passed)")


def test_probe_cli_exits_one_when_the_gate_fails_and_two_for_a_malformed_key(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """fim probe CLI · exits 1 when the gate fails and 2 for a malformed key."""
    _patch_network(monkeypatch, lambda request: httpx.Response(404))

    assert main(["fim", "probe", "--keys", OK_KEY]) == 1
    assert capsys.readouterr().out.splitlines()[-1].endswith("(failed)")
    with pytest.raises(SystemExit) as raised:
        main(["fim", "probe", "--keys", "not-a-key"])
    assert raised.value.code == 2
