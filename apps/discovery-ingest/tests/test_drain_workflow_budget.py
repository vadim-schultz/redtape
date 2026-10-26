"""The drain workflow guards itself with the Actions-minutes budget (chapter 23)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

WORKFLOW = Path(__file__).resolve().parents[3] / ".github" / "workflows" / "discovery-drain.yml"
BUDGET_CHECK = "python -m discovery_ingest budget show"
REPORT = "python -m discovery_ingest budget report-minutes"


@pytest.fixture(scope="module")
def job() -> dict[str, Any]:
    document = yaml.safe_load(WORKFLOW.read_text())
    assert isinstance(document, dict)
    return document["jobs"]["drain"]


def _index(steps: list[dict[str, Any]], needle: str) -> int:
    matches = [i for i, step in enumerate(steps) if needle in str(step.get("run", ""))]
    assert len(matches) == 1, f"expected one step running {needle!r}"
    return matches[0]


def test_the_job_keeps_its_timeout_and_requires_that_many_minutes_before_running(job: dict[str, Any]) -> None:
    steps = job["steps"]
    check = steps[_index(steps, BUDGET_CHECK)]

    required = re.search(r"--require-remaining\s+\"?actions_minutes=(\d+)", check["run"])
    assert required is not None
    assert int(required.group(1)) == job["timeout-minutes"]


def test_a_budget_step_precedes_the_drain_and_the_drain_steps_wait_for_it(job: dict[str, Any]) -> None:
    steps = job["steps"]
    budget, drain = _index(steps, BUDGET_CHECK), _index(steps, "worker drain")

    assert budget < drain
    assert steps[budget]["id"] == "budget"
    assert "skip=true" in steps[budget]["run"]
    for step in steps[drain:]:
        if REPORT not in step.get("run", ""):
            assert "steps.budget.outputs.skip" in step["if"], step["name"]


def test_the_start_time_is_recorded_before_anything_else_runs(job: dict[str, Any]) -> None:
    first = job["steps"][0]

    assert "date +%s" in first["run"]
    assert "GITHUB_ENV" in first["run"]


def test_an_always_step_reports_the_minutes_after_every_other_step(job: dict[str, Any]) -> None:
    steps = job["steps"]
    report = steps[_index(steps, REPORT)]

    assert report["if"] == "always()"
    assert report["name"] == steps[-1]["name"]
    assert "+ 1" in report["run"]


def test_the_existing_inputs_and_drain_arguments_are_unchanged() -> None:
    document = yaml.safe_load(WORKFLOW.read_text())
    inputs = document[True]["workflow_dispatch"]["inputs"]

    assert set(inputs) == {"max_tasks", "max_batches", "time_budget_seconds", "kinds"}
    assert inputs["kinds"]["default"] == "fetch_url,enrich_metadata,harvest_payload"
