"""The render job passes RENDER_FUSED_SCREENSHOT, default off, and no stage precheck reads Actions minutes (chapter 16, D16, D17)."""

from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import Any

import pytest
import yaml
from discovery_ingest.config import load_browser_settings

WORKFLOWS = Path(__file__).resolve().parents[3] / ".github" / "workflows"
RENDER = "discovery-render.yml"
FLAG = "RENDER_FUSED_SCREENSHOT"
STAGE_WORKFLOWS = (
    "discovery-drain.yml",
    "discovery-render.yml",
    "discovery-screenshot.yml",
    "discovery-embed.yml",
    "discovery-translate.yml",
    "discovery-llm.yml",
)
# The drain has no budget call left after chapter 16, so only these five keep one.
BUDGETED_WORKFLOWS = tuple(name for name in STAGE_WORKFLOWS if name != "discovery-drain.yml")


def _document(name: str) -> dict[Any, Any]:
    """Return the parsed workflow ``name``."""
    document = yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def _budget_lines(name: str) -> list[str]:
    """Return every line of ``name`` that runs a ``budget show`` call, across all jobs and steps."""
    lines: list[str] = []
    for job in _document(name)["jobs"].values():
        for step in job["steps"]:
            lines += [line for line in str(step.get("run", "")).splitlines() if "budget show" in line]
    return lines


def _budget_arguments(name: str) -> list[str]:
    """Return the arguments of the single ``budget show`` call in ``name``, without the shell's exit-code tail."""
    lines = _budget_lines(name)
    assert len(lines) == 1, f"{name}: expected one budget show call, found {len(lines)}"
    tail = lines[0].split("budget show", 1)[1].split("||", 1)[0]
    return shlex.split(tail)


def test_the_render_job_passes_render_fused_screenshot_from_its_variable_defaulting_to_false() -> None:
    """render workflow · the job env carries RENDER_FUSED_SCREENSHOT from the repository variable, default 'false'."""
    env = _document(RENDER)["jobs"]["drain"]["env"]

    assert env[FLAG] == "${{ vars.RENDER_FUSED_SCREENSHOT || 'false' }}"


def test_the_render_job_never_enables_the_fused_path_when_the_variable_is_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """render workflow · an unset variable resolves to the 'false' default, and the config reads it as off."""
    expression = _document(RENDER)["jobs"]["drain"]["env"][FLAG]
    default = re.fullmatch(r"\$\{\{ vars\.RENDER_FUSED_SCREENSHOT \|\| '([^']*)' \}\}", expression)

    assert default is not None and default.group(1) == "false"
    monkeypatch.setenv(FLAG, default.group(1))
    assert load_browser_settings().render_fused_screenshot is False


def test_no_stage_workflow_asks_the_budget_for_actions_minutes() -> None:
    """workflow · negative grep: no budget show call in a stage workflow names actions_minutes (D17)."""
    offenders = [
        f"{name}: {line.strip()}"
        for name in STAGE_WORKFLOWS
        for line in _budget_lines(name)
        if "actions_minutes" in line
    ]

    assert offenders == []
    assert all(_budget_lines(name) for name in BUDGETED_WORKFLOWS)


def test_render_and_screenshot_still_skip_when_their_browser_seconds_are_used_up() -> None:
    """workflow · the precheck is exactly budget show for browser_seconds, skipping under 30 seconds."""
    for name in ("discovery-render.yml", "discovery-screenshot.yml"):
        assert _budget_arguments(name) == ["--resource", "browser_seconds", "--require-remaining", "browser_seconds=30"], name


def test_embed_and_llm_still_skip_when_their_neuron_budget_is_short() -> None:
    """workflow · the precheck is exactly budget show for neurons, with the floors 100 (embed) and 300 (llm)."""
    assert _budget_arguments("discovery-embed.yml") == ["--resource", "neurons", "--require-remaining", "neurons=100"]
    assert _budget_arguments("discovery-llm.yml") == ["--resource", "neurons", "--require-remaining", "neurons=300"]
