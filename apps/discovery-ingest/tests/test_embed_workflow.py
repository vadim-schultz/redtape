"""The discovery-embed workflow: gated schedule, ledger and queue prechecks, bounded drain, minutes report (search-first C6)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

PATH = Path(__file__).resolve().parents[3] / ".github" / "workflows" / "discovery-embed.yml"
BUDGET_CHECK = "python -m discovery_ingest budget show"
SUMMARY_CHECK = "python -m discovery_ingest embed summary --require-pending"
DRAIN = "python -m discovery_ingest embed drain"
REPORT = "python -m discovery_ingest budget report-minutes"
SECRETS = {"DISCOVERY_API_URL", "DISCOVERY_API_KEY", "CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_AI_API_TOKEN"}


@pytest.fixture(scope="module")
def document() -> dict[Any, Any]:
    loaded = yaml.safe_load(PATH.read_text())
    assert isinstance(loaded, dict)
    return loaded


@pytest.fixture(scope="module")
def job(document: dict[Any, Any]) -> dict[str, Any]:
    drain = document["jobs"]["drain"]
    assert isinstance(drain, dict)
    return drain


def _index(steps: list[dict[str, Any]], needle: str) -> int:
    matches = [i for i, step in enumerate(steps) if needle in str(step.get("run", ""))]
    assert len(matches) == 1, f"expected one step running {needle!r}"
    return matches[0]


def test_the_schedule_is_gated_by_the_embed_variable_and_dispatch_always_works(
    document: dict[Any, Any], job: dict[str, Any]
) -> None:
    """workflow · schedule plus workflow_dispatch; the job runs on dispatch or when DISCOVERY_EMBED_SCHEDULE is enabled."""
    triggers = document[True]
    assert triggers["schedule"] and "workflow_dispatch" in triggers
    assert job["if"] == "github.event_name == 'workflow_dispatch' || vars.DISCOVERY_EMBED_SCHEDULE == 'enabled'"


def test_it_shares_the_pipeline_concurrency_group_and_never_cancels_a_running_drain(document: dict[Any, Any]) -> None:
    """workflow · group discovery-pipeline, cancel-in-progress false, read-only permissions."""
    assert document["concurrency"] == {"group": "discovery-pipeline", "cancel-in-progress": False}
    assert document["permissions"] == {"contents": "read"}


def test_the_job_has_a_timeout_and_requires_that_many_minutes_and_some_neurons(job: dict[str, Any]) -> None:
    """workflow · the ledger precheck requires the job's timeout in minutes and a floor of neurons."""
    check = job["steps"][_index(job["steps"], BUDGET_CHECK)]["run"]

    minutes = re.search(r"--require-remaining\s+actions_minutes=(\d+)", check)
    assert minutes is not None and int(minutes.group(1)) == job["timeout-minutes"]
    assert re.search(r"--require-remaining\s+neurons=\d+", check)


def test_the_documented_skip_when_nothing_is_pending_precedes_the_drain_and_gates_every_later_step(
    job: dict[str, Any],
) -> None:
    """workflow · documents the skip when pending_ready is 0: the summary precheck sits before the drain and sets skip."""
    steps = job["steps"]
    summary, drain = _index(steps, SUMMARY_CHECK), _index(steps, DRAIN)

    assert _index(steps, BUDGET_CHECK) < summary < drain
    assert "skip=true" in steps[summary]["run"] and "nothing to embed" in steps[summary]["run"]
    for step in steps[summary + 1 :]:
        if REPORT not in step.get("run", ""):
            assert "steps.budget.outputs.skip" in step["if"], step["name"]


def test_the_drain_writes_a_report_and_the_job_fails_only_when_it_did_not_succeed(job: dict[str, Any]) -> None:
    """workflow · tee drain-report.json, summary in the job page, failure only when succeeded is false."""
    steps = job["steps"]

    assert "tee drain-report.json" in steps[_index(steps, DRAIN)]["run"]
    assert "GITHUB_STEP_SUMMARY" in steps[_index(steps, 'echo "### Embedding drain report"')]["run"]
    assert "get('succeeded')" in steps[_index(steps, "json.load(open('drain-report.json'))")]["run"]


def test_an_always_step_reports_the_minutes_last(job: dict[str, Any]) -> None:
    """workflow · the minutes report runs even after a failure, last, with the runner-setup minute added."""
    steps = job["steps"]
    report = steps[_index(steps, REPORT)]

    assert report["if"] == "always()" and report["name"] == steps[-1]["name"] and "+ 1" in report["run"]
    assert "date +%s" in steps[0]["run"] and "GITHUB_ENV" in steps[0]["run"]


def test_the_four_secrets_reach_the_job_and_none_is_echoed(job: dict[str, Any]) -> None:
    """workflow · API URL and key plus the Workers AI account and token as secrets; no step prints them."""
    env = job["env"]
    assert {name for name, value in env.items() if "secrets." in str(value)} == SECRETS
    for step in job["steps"]:
        run = str(step.get("run", ""))
        assert not re.search(r"echo[^\n]*\$\{?(CLOUDFLARE_AI_API_TOKEN|DISCOVERY_API_KEY)", run)


def test_the_dispatch_inputs_default_to_a_bounded_drain(document: dict[Any, Any], job: dict[str, Any]) -> None:
    """workflow · every bound is an input with a default, passed to the drain command."""
    inputs = document[True]["workflow_dispatch"]["inputs"]

    assert set(inputs) == {"max_tasks", "max_batches", "time_budget_seconds", "neuron_budget"}
    run = job["steps"][_index(job["steps"], DRAIN)]["run"]
    for flag in ("--max-tasks", "--max-batches", "--time-budget-seconds", "--neuron-budget"):
        assert flag in run
