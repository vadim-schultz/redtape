"""The browser workflows: the probe is manual and uses only the Cloudflare secrets (chapter 15)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

WORKFLOWS = Path(__file__).resolve().parents[3] / ".github" / "workflows"


def _load(name: str) -> dict[Any, Any]:
    document = yaml.safe_load((WORKFLOWS / name).read_text())
    assert isinstance(document, dict)
    return document


def test_the_probe_workflow_is_manual_and_uses_only_the_cloudflare_secrets() -> None:
    """probe workflow · workflow_dispatch only; no Discovery API secret reaches it."""
    document = _load("discovery-browser-probe.yml")
    text = (WORKFLOWS / "discovery-browser-probe.yml").read_text()

    assert list(document[True]) == ["workflow_dispatch"]
    assert "secrets.CLOUDFLARE_ACCOUNT_ID" in text and "secrets.CLOUDFLARE_BROWSER_API_TOKEN" in text
    assert "DISCOVERY_API" not in text


def test_the_probe_workflow_runs_the_probe_command_and_fails_when_it_was_refused() -> None:
    """probe workflow · runs browser probe and fails the job on a non-zero probe exit."""
    steps = _load("discovery-browser-probe.yml")["jobs"]["probe"]["steps"]
    runs = "\n".join(str(step.get("run", "")) for step in steps)

    assert "python -m discovery_ingest browser probe" in runs
    assert 'test "${probe_exit:-1}" = "0"' in steps[-1]["run"]


RENDER = "discovery-render.yml"
BUDGET_CHECK = "python -m discovery_ingest budget show"
REPORT = "python -m discovery_ingest budget report-minutes"


def _render_job() -> dict[str, Any]:
    job = _load(RENDER)["jobs"]["drain"]
    assert isinstance(job, dict)
    return job


def _index(steps: list[dict[str, Any]], needle: str) -> int:
    matches = [i for i, step in enumerate(steps) if needle in str(step.get("run", ""))]
    assert len(matches) == 1, f"expected one step running {needle!r}"
    return matches[0]


def test_the_render_workflow_is_dispatched_with_the_browser_inputs_and_a_gated_daily_schedule() -> None:
    """render workflow · dispatch inputs and defaults; the 03:00 UTC schedule is gated by a variable."""
    document = _load(RENDER)
    inputs = document[True]["workflow_dispatch"]["inputs"]

    assert {name: spec["default"] for name, spec in inputs.items()} == {
        "max_tasks": "5",
        "max_batches": "40",
        "time_budget_seconds": "900",
        "browser_budget_seconds": "570",
        "kinds": "render_page",
    }
    assert document[True]["schedule"] == [{"cron": "0 3 * * *"}]
    assert "vars.DISCOVERY_RENDER_SCHEDULE == 'enabled'" in _render_job()["if"]


def test_the_render_workflow_default_and_fallback_browser_budget_is_570() -> None:
    """render workflow · the dispatch default and the scheduled-run fallback are both 570 seconds."""
    text = (WORKFLOWS / RENDER).read_text()
    env = _render_job()["env"]

    assert env["BROWSER_BUDGET_SECONDS"] == "${{ inputs.browser_budget_seconds || '570' }}"
    assert "480" not in text


def test_the_render_workflow_shares_the_drain_concurrency_group_and_has_the_four_secrets() -> None:
    """render workflow · same concurrency group as the drain; Discovery and Cloudflare secrets only."""
    document = _load(RENDER)
    env = _render_job()["env"]

    assert document["concurrency"] == {"group": "discovery-pipeline", "cancel-in-progress": False}
    assert {name for name, value in env.items() if "secrets." in str(value)} == {
        "DISCOVERY_API_URL",
        "DISCOVERY_API_KEY",
        "CLOUDFLARE_ACCOUNT_ID",
        "CLOUDFLARE_BROWSER_API_TOKEN",
    }


def test_the_render_job_requires_its_timeout_in_minutes_and_30_browser_seconds_before_draining() -> None:
    """render workflow · the budget step skips the drain when minutes or browser seconds are gone."""
    job = _render_job()
    steps = job["steps"]
    check = steps[_index(steps, BUDGET_CHECK)]

    assert f"actions_minutes={job['timeout-minutes']}" in check["run"]
    assert "--require-remaining browser_seconds=30" in check["run"]
    assert check["id"] == "budget" and "skip=true" in check["run"]
    drain = _index(steps, "worker drain")
    assert _index(steps, BUDGET_CHECK) < drain
    for step in steps[drain:]:
        if REPORT not in step.get("run", ""):
            assert "steps.budget.outputs.skip" in step["if"], step["name"]


def test_the_render_job_records_its_start_and_reports_minutes_in_a_final_always_step() -> None:
    """render workflow · first step records the start time; the last step reports minutes with if: always()."""
    steps = _render_job()["steps"]

    assert "DRAIN_STARTED_AT" in steps[0]["run"] and "GITHUB_ENV" in steps[0]["run"]
    assert steps[_index(steps, REPORT)] is steps[-1] and steps[-1]["if"] == "always()"
    assert "+ 1" in steps[-1]["run"]


def test_the_render_job_drains_with_both_budgets_and_fails_only_when_the_report_says_so() -> None:
    """render workflow · the drain passes the run and browser budgets; the job fails on succeeded=false."""
    steps = _render_job()["steps"]
    drain = steps[_index(steps, "worker drain")]["run"]
    gate = steps[-2]["run"]

    for flag in ("--max-tasks", "--max-batches", "--time-budget-seconds", "--browser-budget-seconds", "--kinds"):
        assert flag in drain
    assert "get('succeeded')" in gate
