"""``pipeline plan`` and ``pipeline run`` on the command line: the JSON plan, the flag, and a ledger that cannot be read."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest
from discovery_ingest.cli import main
from discovery_ingest.operations.pipeline import RUN_CEILING_SECONDS

from pipeline_fakes import row

API_BASE = "https://redtape.test"
_REAL_HTTPX_CLIENT = httpx.Client
Handler = Callable[[httpx.Request], httpx.Response]


def _answer(request: httpx.Request) -> httpx.Response:
    """Answer each plan read from fixed numbers: embed has 40 ready, render 6, and the ledger has room."""
    path = request.url.path
    if path.endswith("/budgets"):
        rows = [row("browser_seconds", 400.0), row("neurons", 3000.0)]
        return httpx.Response(200, json={"items": [item.model_dump(mode="json") for item in rows]})
    if path.endswith("/tasks/summary"):
        kind = request.url.params.get_list("kinds")
        ready = 6 if kind == ["render_page"] else 0
        return httpx.Response(200, json=_task_summary(ready))
    if path.endswith("/embeddings/summary"):
        return httpx.Response(200, json={"pending_ready": 40, "claimed": 0, "failed": 0, "stale_candidates": 0})
    if path.endswith("/translations/summary"):
        return httpx.Response(200, json={"locales": []})
    if path.endswith("/snapshots/summary"):
        return httpx.Response(200, json={"locales": []})
    if path.endswith("/artifacts/missing-screenshot"):
        return httpx.Response(200, json={"items": []})
    return httpx.Response(404)


def _task_summary(ready: int) -> dict[str, int]:
    return {
        "pending_ready": ready,
        "pending_delayed": 0,
        "claimed": 0,
        "claimed_stale": 0,
        "completed": 0,
        "failed": 0,
    }


@pytest.fixture
def serve(monkeypatch: pytest.MonkeyPatch) -> Callable[[Handler], list[httpx.Request]]:
    """Point the CLI at a fake API whose handler is given; return the requests it saw."""
    monkeypatch.setenv("DISCOVERY_API_URL", API_BASE)
    monkeypatch.setenv("DISCOVERY_API_KEY", "test-machine-key")
    monkeypatch.setenv("LLM_MODEL", "@cf/qwen/qwen3-30b-a3b-fp8")

    def install(handler: Handler) -> list[httpx.Request]:
        seen: list[httpx.Request] = []

        def recording(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return handler(request)

        def factory(**kwargs: Any) -> httpx.Client:
            kwargs["transport"] = httpx.MockTransport(recording)
            return _REAL_HTTPX_CLIENT(**kwargs)

        monkeypatch.setattr("discovery_ingest.client.http_client.httpx.Client", factory)
        return seen

    return install


def test_plan_prints_the_stages_with_ready_work_and_their_caps_as_json(
    serve: Callable[[Handler], list[httpx.Request]], capsys: pytest.CaptureFixture[str]
) -> None:
    serve(_answer)

    assert main(["pipeline", "plan"]) == 0

    plan = json.loads(capsys.readouterr().out)
    stages = {item["stage"]: item for item in plan["stages"]}
    assert stages["embed"]["ready"] == 40
    assert stages["embed"]["caps"] == {"neurons": 2000.0}
    assert stages["render"]["caps"] == {"browser_seconds": 400.0}
    assert {"stage": "seed", "phase": 1, "reason": "no ready work"} in [
        {key: item[key] for key in ("stage", "phase", "reason")} for item in plan["omitted"]
    ]
    assert plan["ceiling_seconds"] == RUN_CEILING_SECONDS


def test_plan_exits_1_when_the_ledger_cannot_be_read(
    serve: Callable[[Handler], list[httpx.Request]], capsys: pytest.CaptureFixture[str]
) -> None:
    serve(lambda request: httpx.Response(500, json={"detail": "down"}))

    assert main(["pipeline", "plan"]) == 1
    assert "pipeline command failed" in capsys.readouterr().err
