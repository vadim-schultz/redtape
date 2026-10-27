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
