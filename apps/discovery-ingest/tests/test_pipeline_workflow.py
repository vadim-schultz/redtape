"""The daily pipeline workflow: the flag gate, the two slots, the shared group, one orchestrator command, and the stage schedules (chapter 12)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml
from discovery_ingest.operations.pipeline import RUN_CEILING_SECONDS

WORKFLOWS = Path(__file__).resolve().parents[3] / ".github" / "workflows"
DAILY = WORKFLOWS / "discovery-daily.yml"
STAGE_WORKFLOWS = (
    "discovery-drain.yml",
    "discovery-render.yml",
    "discovery-extract.yml",
    "discovery-llm.yml",
    "discovery-screenshot.yml",
    "discovery-embed.yml",
    "discovery-translate.yml",
)


def _load(path: Path) -> dict[str, Any]:
    assert path.exists(), f"{path.name} is missing from .github/workflows"
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def _triggers(document: dict[str, Any]) -> dict[str, Any]:
    # YAML 1.1 reads the bare key `on` as boolean True.
    return document.get("on", document.get(True))


def _job() -> dict[str, Any]:
    return _load(DAILY)["jobs"]["pipeline"]


def flag_gate(expression: str, *, flag: str | None) -> bool:
    """Evaluate the job ``if`` for a repository variable (``None`` means unset), as GitHub does for this comparison."""
    text = re.sub(r"^\$\{\{\s*(.*?)\s*\}\}$", r"\1", expression.strip())
    text = text.replace("vars.PIPELINE_ORCHESTRATOR", repr(flag or ""))
    return bool(eval(text, {"__builtins__": {}}, {}))


@pytest.mark.parametrize("flag", [None, "", "disabled"])
def test_the_daily_workflow_does_nothing_when_the_flag_is_off(flag: str | None) -> None:
    assert flag_gate(_job()["if"], flag=flag) is False


def test_the_daily_workflow_runs_when_the_flag_is_enabled() -> None:
    assert flag_gate(_job()["if"], flag="enabled") is True


def test_the_daily_workflow_has_two_off_peak_slots_and_the_shared_concurrency_group() -> None:
    document = _load(DAILY)
    crons = [slot["cron"] for slot in _triggers(document)["schedule"]]

    assert len(crons) == 2
    assert all(cron.split()[0] not in ("0", "00") for cron in crons)
    assert document["concurrency"] == {"group": "discovery-pipeline", "cancel-in-progress": False}


def test_the_daily_job_runs_the_orchestrator_as_one_command_with_the_flag_in_its_environment() -> None:
    job = _job()
    runs = [step.get("run", "") for step in job["steps"]]

    assert job["env"]["PIPELINE_ORCHESTRATOR"] == "${{ vars.PIPELINE_ORCHESTRATOR }}"
    assert sum("python -m discovery_ingest pipeline run" in run for run in runs) == 1
    assert not any("python -m discovery_ingest pipeline plan" in run for run in runs)


def test_the_daily_job_takes_the_translate_environment_for_the_azure_secrets() -> None:
    assert _job()["environment"] == "discovery-translate"


def test_the_job_timeout_is_above_the_run_ceiling_so_the_ceiling_fires_first() -> None:
    assert _job()["timeout-minutes"] * 60 > RUN_CEILING_SECONDS


@pytest.mark.parametrize("name", STAGE_WORKFLOWS)
def test_the_stage_workflows_keep_their_schedules_until_the_flag_has_run_a_day(name: str) -> None:
    assert _triggers(_load(WORKFLOWS / name))["schedule"]
