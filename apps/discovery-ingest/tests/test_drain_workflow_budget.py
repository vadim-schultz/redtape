"""The drain workflow has no budget precheck: Actions minutes were its only resource, and D17 removes it (chapter 16)."""

from __future__ import annotations

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


def test_the_job_keeps_its_timeout_and_has_no_budget_precheck(job: dict[str, Any]) -> None:
    assert job["timeout-minutes"] == 30
    assert not any(BUDGET_CHECK in str(step.get("run", "")) for step in job["steps"])


def test_the_drain_runs_after_the_health_wait_and_no_step_waits_for_a_budget_skip(job: dict[str, Any]) -> None:
    steps = job["steps"]

    assert _index(steps, "wait_for_api") < _index(steps, "worker drain")
    for step in steps:
        assert "steps.budget" not in str(step.get("if", "")), step["name"]


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
