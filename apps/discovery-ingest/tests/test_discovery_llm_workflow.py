"""The discovery-llm workflow: bounded, budget-guarded, gated schedule, four secrets (chapter E7, Loop C)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml
from discovery_ingest.cli import _build_parser, _drain_policy

NAME = "discovery-llm.yml"
PATH = Path(__file__).resolve().parents[3] / ".github" / "workflows" / NAME
BUDGET_CHECK = "python -m discovery_ingest budget show"
REPORT = "python -m discovery_ingest budget report-minutes"
DRAIN = "python -m discovery_ingest worker drain"
ENV_NAMES = {
    "max_tasks": "MAX_TASKS",
    "max_batches": "MAX_BATCHES",
    "time_budget_seconds": "TIME_BUDGET_SECONDS",
    "neuron_budget": "NEURON_BUDGET",
    "kinds": "TASK_KINDS",
}
SECRETS = {"DISCOVERY_API_URL", "DISCOVERY_API_KEY", "CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_AI_API_TOKEN"}
DEFAULTS = {
    "max_tasks": "5",
    "max_batches": "20",
    "time_budget_seconds": "600",
    "neuron_budget": "2500",
    "kinds": "llm_extract",
}


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


def test_the_job_has_a_timeout_a_budget_skip_an_always_minutes_step_and_the_shared_concurrency_group(
    document: dict[Any, Any], job: dict[str, Any]
) -> None:
    """discovery-llm.yml · timeout-minutes 20, skip step before the drain, always-run minutes step last, group discovery-drain."""
    steps = job["steps"]
    check = steps[_index(steps, BUDGET_CHECK)]
    drain = _index(steps, DRAIN)

    assert job["timeout-minutes"] == 20
    assert document["concurrency"] == {"group": "discovery-drain", "cancel-in-progress": False}
    assert (
        f"actions_minutes={job['timeout-minutes']}" in check["run"]
        and "--require-remaining neurons=300" in check["run"]
    )
    assert check["id"] == "budget" and "skip=true" in check["run"] and _index(steps, BUDGET_CHECK) < drain
    assert steps[_index(steps, REPORT)] is steps[-1] and steps[-1]["if"] == "always()"
    assert "DRAIN_STARTED_AT" in steps[0]["run"]


def test_every_step_after_the_skip_check_waits_for_it_except_the_minutes_report(job: dict[str, Any]) -> None:
    """discovery-llm.yml · a skipped run neither waits for the API nor drains; only the minutes are still reported."""
    steps = job["steps"]
    for step in steps[_index(steps, BUDGET_CHECK) + 1 :]:
        if REPORT not in step.get("run", ""):
            assert "steps.budget.outputs.skip" in step["if"], step["name"]


def test_the_schedule_is_daily_at_6_utc_and_gated_by_the_repository_variable(
    document: dict[Any, Any], job: dict[str, Any]
) -> None:
    """discovery-llm.yml · cron 0 6 * * *; a scheduled run needs DISCOVERY_LLM_SCHEDULE == enabled, a manual one does not."""
    assert document[True]["schedule"] == [{"cron": "0 6 * * *"}]
    assert job["if"] == "github.event_name == 'workflow_dispatch' || vars.DISCOVERY_LLM_SCHEDULE == 'enabled'"


def test_the_job_passes_only_the_four_named_secrets_and_installs_no_extra(job: dict[str, Any]) -> None:
    """discovery-llm.yml · four secrets in env, none elsewhere; pip install -e . without extras."""
    text = PATH.read_text()
    env = job["env"]
    steps = job["steps"]

    assert {name for name, value in env.items() if "secrets." in str(value)} == SECRETS
    assert set(re.findall(r"secrets\.(\w+)", text)) == SECRETS
    install = steps[_index(steps, "pip install")]["run"]
    assert "pip install -e ." in install and "[" not in install


def test_the_inputs_have_the_bounded_defaults_and_the_model_is_required_without_a_default(
    document: dict[Any, Any],
) -> None:
    """discovery-llm.yml · neuron_budget 2500 (not 4000); llm_model is required, has no default and no model id appears."""
    inputs = document[True]["workflow_dispatch"]["inputs"]

    assert {name: spec["default"] for name, spec in inputs.items() if name != "llm_model"} == DEFAULTS
    assert inputs["llm_model"]["required"] is True and "default" not in inputs["llm_model"]
    assert "@cf/" not in PATH.read_text()


def test_the_workflow_inputs_match_the_drain_flags_of_the_command_line(job: dict[str, Any]) -> None:
    """discovery-llm.yml · each bound input is a worker drain flag, the drain passes them all and the CLI accepts them."""
    steps = job["steps"]
    command = steps[_index(steps, DRAIN)]["run"]
    flags = re.findall(r"--[a-z-]+", command)
    env = job["env"]
    expected = [f"--{name.replace('_', '-')}" for name in DEFAULTS]

    assert sorted(flags) == sorted(expected)
    assert all(env_name in env and f"${{{env_name}}}" in command for env_name in ENV_NAMES.values())
    values = [value for name in DEFAULTS for value in (f"--{name.replace('_', '-')}", DEFAULTS[name])]
    policy = _drain_policy(_build_parser().parse_args(["worker", "drain", *values]))
    assert (policy.max_tasks, policy.max_batches, policy.neuron_budget) == (5, 20, 2500)


def test_the_model_comes_from_the_input_or_the_variable_and_an_unset_model_skips_with_a_message(
    job: dict[str, Any],
) -> None:
    """discovery-llm.yml · LLM_MODEL is the input or DISCOVERY_LLM_MODEL; empty means skip=true and a summary line."""
    steps = job["steps"]
    check = steps[_index(steps, BUDGET_CHECK)]["run"]

    assert job["env"]["LLM_MODEL"] == "${{ inputs.llm_model || vars.DISCOVERY_LLM_MODEL }}"
    assert 'if [ -z "${LLM_MODEL}" ]' in check and "DISCOVERY_LLM_MODEL" in check
    assert check.index("LLM_MODEL") < check.index(BUDGET_CHECK) and "GITHUB_STEP_SUMMARY" in check


def test_the_job_fails_only_when_the_report_says_the_drain_did_not_succeed(job: dict[str, Any]) -> None:
    """discovery-llm.yml · limits (llm_budget, llm_quota, db_limit, ...) succeed; succeeded=false fails the job."""
    steps = job["steps"]
    gate = steps[-2]["run"]

    assert "get('succeeded')" in gate and "drain-report.json" in gate
    assert "steps.budget.outputs.skip" in steps[-2]["if"]
