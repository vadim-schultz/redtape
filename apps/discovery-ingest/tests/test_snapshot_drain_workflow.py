"""The snapshot job of discovery-translate: after the card drain, in the pipeline group, off until SNAPSHOT_TRANSLATE_SCHEDULE
is enabled, with its own character precheck."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

PATH = Path(__file__).resolve().parents[3] / ".github" / "workflows" / "discovery-translate.yml"
SNAPSHOT_GATE = "always() && vars.SNAPSHOT_TRANSLATE_SCHEDULE == 'enabled'"
SUMMARY_CHECK = "python -m discovery_ingest translate summary --unit snapshot --require-pending"
DRAIN = "python -m discovery_ingest translate drain --unit snapshot --max-tasks 5"
BUDGET_CHECK = "python -m discovery_ingest budget show"
REPORT = "python -m discovery_ingest budget report-minutes"


@pytest.fixture(scope="module")
def document() -> dict[Any, Any]:
    loaded = yaml.safe_load(PATH.read_text())
    assert isinstance(loaded, dict)
    return loaded


@pytest.fixture(scope="module")
def job(document: dict[Any, Any]) -> dict[str, Any]:
    snapshot = document["jobs"]["snapshot-drain"]
    assert isinstance(snapshot, dict)
    return snapshot


def _step(job: dict[str, Any], needle: str) -> dict[str, Any]:
    matches = [step for step in job["steps"] if needle in str(step.get("run", ""))]
    assert len(matches) == 1, f"expected one step running {needle!r}"
    return matches[0]


def test_the_snapshot_job_is_skipped_unless_snapshot_translate_schedule_is_enabled(job: dict[str, Any]) -> None:
    """workflow · the snapshot job runs only when SNAPSHOT_TRANSLATE_SCHEDULE is enabled; it is off by default."""
    assert job["if"] == SNAPSHOT_GATE


def test_the_snapshot_job_runs_after_the_card_drain_and_is_not_a_card_step(
    document: dict[Any, Any], job: dict[str, Any]
) -> None:
    """workflow · the snapshot job needs the card drain, so it runs after it, and the card job's own gate is unchanged."""
    assert job["needs"] == "drain"
    assert document["jobs"]["drain"]["if"] == (
        "github.event_name == 'workflow_dispatch' || vars.DISCOVERY_TRANSLATE_SCHEDULE == 'enabled'"
    )


def test_it_drains_snapshot_pages_five_at_a_time_and_checks_the_queue_first(job: dict[str, Any]) -> None:
    """workflow · the queue check and the drain use the snapshot unit, and a claim asks for at most five pages."""
    steps = job["steps"]
    summary, drain = _step(job, SUMMARY_CHECK), _step(job, DRAIN)

    assert steps.index(summary) < steps.index(drain)
    assert "skip=true" in summary["run"] and "nothing to translate" in summary["run"]
    assert "tee snapshot-drain-report.json" in drain["run"]


def test_it_has_its_own_character_precheck_before_the_drain(job: dict[str, Any]) -> None:
    """workflow · the snapshot job checks the monthly character ledger, and the actions minutes, before it claims."""
    steps = job["steps"]
    check = _step(job, BUDGET_CHECK)

    assert steps.index(check) < steps.index(_step(job, DRAIN))
    assert "--resource azure_translator_chars --require-remaining" in check["run"]
    assert "azure_translator_chars=${AZURE_TRANSLATOR_MIN_REMAINING_CHARS}" in check["run"]
    assert "--resource actions_minutes --require-remaining actions_minutes=20" in check["run"]


def test_the_document_share_is_read_from_the_workflow_variable_with_a_default_of_0_6(job: dict[str, Any]) -> None:
    """workflow · AZURE_DOCUMENT_BUDGET_SHARE comes from the repository variable and defaults to 0.6 (the runbook's value)."""
    assert job["env"]["AZURE_DOCUMENT_BUDGET_SHARE"] == "${{ vars.AZURE_DOCUMENT_BUDGET_SHARE || '0.6' }}"


def test_the_azure_secrets_reach_only_this_job_and_are_never_echoed(job: dict[str, Any]) -> None:
    """workflow · the snapshot job reads the Azure key and region from secrets; no step prints them."""
    env = job["env"]

    assert env["AZURE_TRANSLATOR_KEY"] == "${{ secrets.AZURE_TRANSLATOR_KEY }}"
    assert env["AZURE_TRANSLATOR_REGION"] == "${{ secrets.AZURE_TRANSLATOR_REGION }}"
    assert job["environment"] == "discovery-translate"
    for step in job["steps"]:
        assert not re.search(r"echo[^\n]*\$\{?AZURE_TRANSLATOR_KEY", str(step.get("run", "")))


def test_the_report_goes_to_the_job_summary_and_the_job_fails_only_when_the_drain_did_not_succeed(
    job: dict[str, Any],
) -> None:
    """workflow · the drain report goes to the job summary; the job fails only when succeeded is false."""
    summary = _step(job, "Snapshot translation drain report")
    fail_check = _step(job, "json.load(open('snapshot-drain-report.json'))")

    assert "GITHUB_STEP_SUMMARY" in summary["run"]
    assert "get('succeeded')" in fail_check["run"]


def test_it_reports_its_own_actions_minutes_last(job: dict[str, Any]) -> None:
    """workflow · the minutes report runs even after a failure and is the job's last step, with the runner-setup minute."""
    steps = job["steps"]
    report = _step(job, REPORT)

    assert report["if"] == "always()" and report["name"] == steps[-1]["name"] and "+ 1" in report["run"]
    assert "GITHUB_ENV" in steps[0]["run"]
