"""The Workers AI probe workflow is manual and uses only the two Cloudflare secrets (chapter E4, Step 0)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

WORKFLOW = "discovery-llm-probe.yml"
PATH = Path(__file__).resolve().parents[3] / ".github" / "workflows" / WORKFLOW


def _document() -> dict[Any, Any]:
    document = yaml.safe_load(PATH.read_text())
    assert isinstance(document, dict)
    return document


def test_the_probe_workflow_is_manual_and_uses_only_the_cloudflare_secrets() -> None:
    """llm probe workflow · workflow_dispatch only; no Discovery API secret and no browser token reaches it."""
    text = PATH.read_text()

    assert list(_document()[True]) == ["workflow_dispatch"]
    assert "secrets.CLOUDFLARE_ACCOUNT_ID" in text and "secrets.CLOUDFLARE_AI_API_TOKEN" in text
    assert "DISCOVERY_API" not in text and "CLOUDFLARE_BROWSER_API_TOKEN" not in text


def test_the_probe_workflow_runs_the_probe_with_a_neuron_cap_and_fails_on_a_non_zero_exit() -> None:
    """llm probe workflow · runs llm probe over the models and fixture inputs; the last step fails the job."""
    document = _document()
    steps = document["jobs"]["probe"]["steps"]
    runs = "\n".join(str(step.get("run", "")) for step in steps)

    assert "python -m discovery_ingest llm probe" in runs and "--max-neurons" in runs and "--fixture" in runs
    assert set(document[True]["workflow_dispatch"]["inputs"]) == {"models", "fixture", "max_neurons"}
    assert 'test "${probe_exit:-1}" = "0"' in steps[-1]["run"]
