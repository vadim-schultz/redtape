"""Worker-side budget client and guard: a denial is normal, an unreachable ledger never raises (chapter 23)."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest
from discovery_ingest.api_client import DiscoveryMachineApiError, DiscoveryMachineClient
from discovery_ingest.budget import BudgetGuard
from discovery_ingest.cli import main

from run_stub import run_response

API_BASE = "https://redtape.test"
_REAL_HTTPX_CLIENT = httpx.Client
Handler = Callable[[httpx.Request], httpx.Response]


def _row(resource: str, *, used: float = 0, cap: int = 100, exhausted: bool = False) -> dict[str, object]:
    return {
        "resource": resource,
        "period": "2026-10-26",
        "cap": cap,
        "used": used,
        "remaining": max(cap - used, 0),
        "exhausted": exhausted,
    }


def _client(monkeypatch: pytest.MonkeyPatch, handler: Handler) -> DiscoveryMachineClient:
    def factory(**kwargs: Any) -> httpx.Client:
        kwargs["transport"] = httpx.MockTransport(handler)
        return _REAL_HTTPX_CLIENT(**kwargs)

    monkeypatch.setattr("discovery_ingest.api_client.httpx.Client", factory)
    return DiscoveryMachineClient(API_BASE, "test-machine-key")


def _unreachable(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("no route to host")


def test_reserve_is_granted_on_200_and_denied_on_409_without_raising(monkeypatch: pytest.MonkeyPatch) -> None:
    answers = iter([httpx.Response(200, json={"granted": True, "remaining": 40.0}), None])

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/machine/budgets/neurons/reserve")
        assert json.loads(request.content) == {"amount": 60}
        answer = next(answers)
        return answer or httpx.Response(409, json={"granted": False, "remaining": 40.0})

    guard = BudgetGuard(_client(monkeypatch, handler))

    granted = guard.reserve("neurons", 60)
    denied = guard.reserve("neurons", 60)

    assert (granted.granted, granted.remaining, granted.ledger_unavailable) == (True, 40.0, False)
    assert (denied.granted, denied.remaining, denied.ledger_unavailable) == (False, 40.0, False)
    assert guard.ledger_unavailable is False


@pytest.mark.parametrize(
    "handler",
    [lambda request: httpx.Response(503, text="down"), lambda request: httpx.Response(500, text="boom"), _unreachable],
)
def test_reserve_reports_ledger_unavailable_on_a_5xx_or_a_transport_error_without_raising(
    monkeypatch: pytest.MonkeyPatch, handler: Handler
) -> None:
    guard = BudgetGuard(_client(monkeypatch, handler))

    result = guard.reserve("browser_seconds", 30)

    assert (result.granted, result.remaining, result.ledger_unavailable) == (False, None, True)
    assert guard.ledger_unavailable is True


def test_remaining_reads_the_resource_and_reports_an_exhausted_period(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [_row("neurons", used=10), _row("browser_seconds", used=480, cap=480, exhausted=True)]
    guard = BudgetGuard(_client(monkeypatch, lambda request: httpx.Response(200, json={"items": rows})))

    neurons = guard.remaining("neurons")
    browser = guard.remaining("browser_seconds")

    assert (neurons.remaining, neurons.exhausted, neurons.ledger_unavailable) == (90, False, False)
    assert (browser.remaining, browser.exhausted) == (0, True)


def test_remaining_reports_ledger_unavailable_when_the_ledger_cannot_be_read(monkeypatch: pytest.MonkeyPatch) -> None:
    guard = BudgetGuard(_client(monkeypatch, _unreachable))

    result = guard.remaining("neurons")

    assert (result.remaining, result.exhausted, result.ledger_unavailable) == (None, False, True)


def test_a_client_error_other_than_a_denial_is_still_raised_by_the_client(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(monkeypatch, lambda request: httpx.Response(404, json={"detail": "Unknown budget resource"}))

    with pytest.raises(DiscoveryMachineApiError) as raised:
        client.reserve_budget("bananas", 1)

    assert raised.value.status_code == 404


def test_adjust_and_exhaust_are_best_effort_and_report_whether_the_ledger_took_them(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path.rsplit("/", 2)[-1] + ":" + request.content.decode())
        return httpx.Response(200, json=_row("browser_seconds", used=5))

    working = BudgetGuard(_client(monkeypatch, handler))
    broken = BudgetGuard(_client(monkeypatch, _unreachable))

    assert working.adjust("browser_seconds", -2.5) is True
    assert working.exhaust("browser_seconds") is True
    assert broken.adjust("browser_seconds", 1) is False
    assert broken.exhaust("browser_seconds") is False
    assert seen == ['adjust:{"delta":-2.5}', "exhaust:"]
    assert broken.ledger_unavailable is True


@pytest.mark.parametrize(
    ("status", "detail", "expected"),
    [(507, "database_soft_limit", True), (507, "Artifact storage cap reached", False), (503, "database_soft_limit", False)],
)
def test_a_507_with_the_soft_limit_detail_is_recognised_as_the_database_limit(
    status: int, detail: str, expected: bool
) -> None:
    error = DiscoveryMachineApiError(status, json.dumps({"status_code": status, "detail": detail}))

    assert error.is_database_limit is expected


def _drain_handler(ledger: httpx.Response | None) -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        stub = run_response(request)
        if stub is not None:
            return stub
        if request.url.path.endswith("/budgets"):
            return ledger or _unreachable(request)
        return httpx.Response(200, json={"items": []})

    return handler


@pytest.mark.parametrize(
    ("ledger", "unavailable"),
    [(httpx.Response(200, json={"items": [_row("neurons")]}), False), (None, True), (httpx.Response(503), True)],
)
def test_the_drain_report_carries_ledger_unavailable_when_the_ledger_could_not_be_read(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], ledger: httpx.Response | None, unavailable: bool
) -> None:
    monkeypatch.setenv("DISCOVERY_API_URL", API_BASE)
    monkeypatch.setenv("DISCOVERY_API_KEY", "test-machine-key")
    _client(monkeypatch, _drain_handler(ledger))

    exit_code = main(["worker", "drain", "--max-tasks", "1"])

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out)["ledger_unavailable"] is unavailable
