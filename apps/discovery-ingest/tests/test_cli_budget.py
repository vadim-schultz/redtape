"""``budget show`` and ``budget report-minutes`` command line behaviour (chapter 23)."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest
from discovery_ingest.cli import main

API_BASE = "https://redtape.test"
_REAL_HTTPX_CLIENT = httpx.Client
Handler = Callable[[httpx.Request], httpx.Response]


def _row(resource: str, *, remaining: float, exhausted: bool = False) -> dict[str, object]:
    return {
        "resource": resource,
        "period": "2026-10",
        "cap": 400,
        "used": 400 - remaining,
        "remaining": remaining,
        "exhausted": exhausted,
    }


SNAPSHOT = {
    "items": [
        _row("actions_minutes", remaining=100),
        _row("neurons", remaining=0, exhausted=True),
        _row("r2_class_a", remaining=400),
    ]
}


@pytest.fixture
def serve(monkeypatch: pytest.MonkeyPatch) -> Callable[[Handler], list[httpx.Request]]:
    monkeypatch.setenv("DISCOVERY_API_URL", API_BASE)
    monkeypatch.setenv("DISCOVERY_API_KEY", "test-machine-key")

    def install(handler: Handler) -> list[httpx.Request]:
        seen: list[httpx.Request] = []

        def recording(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return handler(request)

        def factory(**kwargs: Any) -> httpx.Client:
            kwargs["transport"] = httpx.MockTransport(recording)
            return _REAL_HTTPX_CLIENT(**kwargs)

        monkeypatch.setattr("discovery_ingest.api_client.httpx.Client", factory)
        return seen

    return install


def _ledger(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json=SNAPSHOT)


def _down(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("unreachable")


def test_show_prints_the_snapshot_as_json_and_filters_by_resource(
    serve: Callable[[Handler], list[httpx.Request]], capsys: pytest.CaptureFixture[str]
) -> None:
    serve(_ledger)

    everything = main(["budget", "show"])
    all_rows = json.loads(capsys.readouterr().out)["items"]
    one = main(["budget", "show", "--resource", "neurons", "--resource", "r2_class_a"])
    some_rows = json.loads(capsys.readouterr().out)["items"]

    assert (everything, one) == (0, 0)
    assert [row["resource"] for row in all_rows] == ["actions_minutes", "neurons", "r2_class_a"]
    assert [row["resource"] for row in some_rows] == ["neurons", "r2_class_a"]


def test_show_exits_0_when_the_required_remaining_is_there(serve: Callable[[Handler], list[httpx.Request]]) -> None:
    serve(_ledger)

    assert main(["budget", "show", "--require-remaining", "actions_minutes=100"]) == 0
    assert main(["budget", "show", "--require-remaining", "actions_minutes=45", "--require-remaining", "r2_class_a=1"]) == 0


def test_show_exits_3_when_a_required_resource_is_short_or_exhausted(
    serve: Callable[[Handler], list[httpx.Request]], capsys: pytest.CaptureFixture[str]
) -> None:
    serve(_ledger)

    short = main(["budget", "show", "--require-remaining", "actions_minutes=101"])
    exhausted = main(["budget", "show", "--require-remaining", "neurons=0"])
    one_of_two = main(["budget", "show", "--require-remaining", "r2_class_a=1", "--require-remaining", "neurons=1"])

    assert (short, exhausted, one_of_two) == (3, 3, 3)
    assert "actions_minutes" in capsys.readouterr().err


def test_show_exits_0_with_a_warning_when_the_ledger_is_unreachable_and_4_with_strict(
    serve: Callable[[Handler], list[httpx.Request]], capsys: pytest.CaptureFixture[str]
) -> None:
    serve(_down)
    required = ["--require-remaining", "actions_minutes=45"]

    lenient = main(["budget", "show", *required])
    warning = capsys.readouterr().err
    strict = main(["budget", "show", *required, "--strict"])

    assert (lenient, strict) == (0, 4)
    assert "ledger" in warning.lower()


def test_show_treats_a_5xx_answer_like_an_unreachable_ledger(serve: Callable[[Handler], list[httpx.Request]]) -> None:
    serve(lambda request: httpx.Response(503, text="down"))

    assert main(["budget", "show", "--require-remaining", "actions_minutes=45"]) == 0
    assert main(["budget", "show", "--require-remaining", "actions_minutes=45", "--strict"]) == 4


@pytest.mark.parametrize("flag", ["actions_minutes", "bananas=5", "actions_minutes=abc", "actions_minutes=-1"])
def test_show_rejects_a_malformed_requirement_before_calling_the_api(
    serve: Callable[[Handler], list[httpx.Request]], flag: str
) -> None:
    seen = serve(_ledger)

    with pytest.raises(SystemExit) as raised:
        main(["budget", "show", "--require-remaining", flag])

    assert raised.value.code == 2
    assert seen == []


def test_report_minutes_posts_the_adjustment_for_actions_minutes(
    serve: Callable[[Handler], list[httpx.Request]],
) -> None:
    seen = serve(lambda request: httpx.Response(200, json=_row("actions_minutes", remaining=95)))

    exit_code = main(["budget", "report-minutes", "--minutes", "5"])

    [request] = seen
    assert exit_code == 0
    assert request.url.path.endswith("/machine/budgets/actions_minutes/adjust")
    assert json.loads(request.content) == {"delta": 5}


def test_report_minutes_rejects_a_non_positive_count_without_calling_the_api(
    serve: Callable[[Handler], list[httpx.Request]],
) -> None:
    seen = serve(_ledger)

    with pytest.raises(SystemExit) as raised:
        main(["budget", "report-minutes", "--minutes", "0"])

    assert raised.value.code == 2
    assert seen == []


def test_report_minutes_warns_and_exits_0_when_the_ledger_is_unreachable(
    serve: Callable[[Handler], list[httpx.Request]], capsys: pytest.CaptureFixture[str]
) -> None:
    serve(_down)

    assert main(["budget", "report-minutes", "--minutes", "3"]) == 0
    assert "ledger" in capsys.readouterr().err.lower()
