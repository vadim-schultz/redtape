"""The catalogue workflows: GovData and PVOG run weekly with variable caps, and the monthly maintenance keeps OpenPLZ only."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

WORKFLOWS = Path(__file__).resolve().parents[3] / ".github" / "workflows"
CATALOGUE = WORKFLOWS / "discovery-catalogue.yml"
MAINTENANCE = WORKFLOWS / "platform-maintenance.yml"
GOVDATA = "python -m discovery_ingest govdata fetch"
PVOG = "python -m discovery_ingest pvog run"
OPENPLZ = "scripts/import_openplz_locations.py"
REFRESH = "python -m discovery_ingest catalogue refresh"


def _load(path: Path) -> dict[Any, Any]:
    loaded = yaml.safe_load(path.read_text())
    assert isinstance(loaded, dict)
    return loaded


@pytest.fixture(scope="module")
def catalogue() -> dict[Any, Any]:
    return _load(CATALOGUE)


@pytest.fixture(scope="module")
def maintenance() -> dict[Any, Any]:
    return _load(MAINTENANCE)


def _run_scripts(job: dict[str, Any]) -> list[str]:
    return [str(step.get("run", "")) for step in job["steps"]]


def test_the_weekly_workflow_runs_govdata_and_pvog_with_the_variable_caps(catalogue: dict[Any, Any]) -> None:
    """catalogue workflow · happy: GovData and PVOG take their page caps from the repository variables, with defaults."""
    job = catalogue["jobs"]["catalogue"]
    scripts = _run_scripts(job)

    assert job["env"]["GOVDATA_MAX_PAGES"] == "${{ vars.CATALOGUE_GOVDATA_MAX_PAGES || '150' }}"
    assert job["env"]["PVOG_MAX_PAGES"] == "${{ vars.CATALOGUE_PVOG_MAX_PAGES || '50' }}"
    assert any(GOVDATA in run and '--max-pages "${GOVDATA_MAX_PAGES}"' in run for run in scripts)
    assert any(PVOG in run and '--max-pages "${PVOG_MAX_PAGES}"' in run for run in scripts)
    assert not any("--max-pages 15" in run or "--max-pages 50" in run for run in scripts)


def test_the_weekly_workflow_is_scheduled_weekly_and_can_be_dispatched(catalogue: dict[Any, Any]) -> None:
    """catalogue workflow · happy: one cron on a single weekday, plus a manual dispatch."""
    triggers = catalogue[True]
    cron = triggers["schedule"][0]["cron"]

    assert re.fullmatch(r"\d+ \d+ \* \* \d", cron) is not None
    assert "workflow_dispatch" in triggers


def test_the_weekly_workflow_shares_the_pipeline_group_and_never_cancels_a_running_ingest(
    catalogue: dict[Any, Any],
) -> None:
    """catalogue workflow · the discovery-pipeline group with cancel-in-progress false, and read-only permissions."""
    assert catalogue["concurrency"] == {"group": "discovery-pipeline", "cancel-in-progress": False}
    assert catalogue["permissions"] == {"contents": "read"}


def test_the_monthly_maintenance_keeps_only_the_openplz_import(maintenance: dict[Any, Any]) -> None:
    """platform maintenance · negative: no catalogue command remains in the monthly workflow, and OpenPLZ still runs."""
    scripts = [run for job in maintenance["jobs"].values() for run in _run_scripts(job)]

    assert not any(GOVDATA in run or PVOG in run for run in scripts)
    assert any(OPENPLZ in run for run in scripts)
    assert set(maintenance["jobs"]) == {"openplz"}


def test_the_monthly_maintenance_no_longer_offers_a_discovery_choice(maintenance: dict[Any, Any]) -> None:
    """platform maintenance · negative: a dispatch with job=discovery is refused, not silently a no-op."""
    choices = maintenance[True]["workflow_dispatch"]["inputs"]["job"]["options"]

    assert choices == ["all", "openplz"]


def test_the_weekly_workflow_refreshes_stale_pages_after_the_ingest_within_the_variable_bound(
    catalogue: dict[Any, Any],
) -> None:
    """catalogue workflow · happy: one refresh step runs after both ingests and takes its bound from the repository variable."""
    job = catalogue["jobs"]["catalogue"]
    scripts = _run_scripts(job)
    refresh = [index for index, run in enumerate(scripts) if REFRESH in run]
    ingest = [index for index, run in enumerate(scripts) if GOVDATA in run or PVOG in run]

    assert job["env"]["REFRESH_MAX_ROWS"] == "${{ vars.CATALOGUE_REFRESH_MAX_ROWS || '0' }}"
    assert len(refresh) == 1 and refresh[0] > max(ingest)
    assert '--max-rows "${REFRESH_MAX_ROWS}"' in scripts[refresh[0]]


def test_the_refresh_is_off_unless_the_variable_is_set(catalogue: dict[Any, Any]) -> None:
    """catalogue workflow · negative: the bound defaults to zero, and no run line names a literal bound."""
    job = catalogue["jobs"]["catalogue"]

    assert job["env"]["REFRESH_MAX_ROWS"].endswith("|| '0' }}")
    assert not any(re.search(r"--max-rows \d", run) for run in _run_scripts(job))
