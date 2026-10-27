"""The fixture-capture workflow is manual, read-only and short (chapter 17, Loop D)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

WORKFLOW = Path(__file__).resolve().parents[3] / ".github" / "workflows" / "discovery-fixture-capture.yml"


def _document() -> dict[Any, Any]:
    document = yaml.safe_load(WORKFLOW.read_text())
    assert isinstance(document, dict)
    return document


def test_the_workflow_is_dispatched_by_hand_with_host_and_limit_inputs() -> None:
    """fixture capture · workflow_dispatch only (no schedule, no push), inputs host and limit."""
    triggers = _document()[True]
    inputs = triggers["workflow_dispatch"]["inputs"]

    assert list(triggers) == ["workflow_dispatch"]
    assert (inputs["host"]["required"], inputs["limit"]["default"]) == (True, "5")


def test_the_workflow_lists_downloads_and_uploads_the_snapshots_with_read_only_permissions() -> None:
    """fixture capture · lists then downloads through the CLI, uploads one Actions artifact, reads contents only."""
    document = _document()
    job = document["jobs"]["capture"]
    runs = "\n".join(str(step.get("run", "")) for step in job["steps"])
    uses = [str(step.get("uses", "")) for step in job["steps"]]

    assert document["permissions"] == {"contents": "read"}
    assert runs.index("artifacts list") < runs.index("artifacts download")
    assert any(name.startswith("actions/upload-artifact@") for name in uses)
    assert job["timeout-minutes"] <= 10


def test_the_workflow_passes_the_inputs_through_the_environment_not_into_the_script() -> None:
    """fixture capture · inputs reach the shell as variables, never interpolated into the script text."""
    job = _document()["jobs"]["capture"]
    runs = "\n".join(str(step.get("run", "")) for step in job["steps"])

    assert "${{" not in runs
    assert set(job["env"]) >= {"DISCOVERY_API_URL", "DISCOVERY_API_KEY", "CAPTURE_HOST", "CAPTURE_LIMIT"}
