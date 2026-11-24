"""Every real invocation in the workflows and operator docs parses, and every workflow flag is in the contract."""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

import pytest

from cli_adapters import accepts, describe
from cli_invocations import INVOCATIONS

REPO = Path(__file__).resolve().parents[3]
WORKFLOW_DIR = REPO / ".github" / "workflows"
WORKFLOWS = sorted([*WORKFLOW_DIR.glob("discovery-*.yml"), WORKFLOW_DIR / "platform-maintenance.yml"])
STATEMENT = re.compile(r"python -m discovery_ingest ([^\n|;&<>]*)")
ARRAY_OPEN = re.compile(r"(?:args=\(|args\+=\()")
FLAG = re.compile(r"--[a-z][a-z-]*")
CONTRACT = {spec.path: spec for spec in describe()}
ARRAY_COMMANDS = (("worker", "drain"), ("browser", "probe"), ("llm", "probe"))


def _statements(text: str) -> Iterator[tuple[tuple[str, str], list[str]]]:
    """Yield the ``(group, command)`` and the flags of every ``python -m discovery_ingest`` statement."""
    joined = text.replace("\\\n", " ")
    for match in STATEMENT.finditer(joined):
        words = match.group(1).split()
        if len(words) >= 2:
            yield (words[0], words[1]), FLAG.findall(match.group(1))


def _array_flags(text: str) -> list[str]:
    """Return the flags written inside ``args=( ... )`` arrays and ``args+=( ... )`` lines."""
    flags: list[str] = []
    inside = False
    for line in text.splitlines():
        if ARRAY_OPEN.search(line):
            inside = ")" not in line.split("(", 1)[1]
            flags += FLAG.findall(line)
        elif inside:
            flags += FLAG.findall(line)
            inside = ")" not in line
    return flags


@pytest.mark.parametrize(
    ("source", "argv"),
    INVOCATIONS,
    ids=[source for source, _argv in INVOCATIONS],
)
def test_workflow_invocations_parse(source: str, argv: list[str]) -> None:
    assert accepts(argv), source


def test_the_workflow_files_are_found() -> None:
    assert len(WORKFLOWS) >= 10
    statements = sum(len(list(_statements(path.read_text(encoding="utf-8")))) for path in WORKFLOWS)
    assert statements >= 20


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda path: path.name)
def test_every_flag_used_in_workflows_is_in_the_contract(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    for command, flags in _statements(text):
        assert command in CONTRACT, f"{path.name}: {command} is not a documented command"
        known = {flag for option in CONTRACT[command].options for flag in option.flags}
        unknown = sorted(set(flags) - known)
        assert not unknown, f"{path.name}: {' '.join(command)} uses {unknown}"
    known_array = {flag for command in ARRAY_COMMANDS for option in CONTRACT[command].options for flag in option.flags}
    unknown_array = sorted(set(_array_flags(text)) - known_array)
    assert not unknown_array, f"{path.name}: argument arrays use {unknown_array}"


def test_budget_show_exit_3_is_the_skip_signal_the_workflows_test_for() -> None:
    # The drain has no budget call after chapter 16, so the five stage workflows that still check a budget carry the signal.
    for name in (
        "discovery-render.yml",
        "discovery-screenshot.yml",
        "discovery-embed.yml",
        "discovery-translate.yml",
        "discovery-llm.yml",
    ):
        text = (WORKFLOW_DIR / name).read_text(encoding="utf-8")
        assert "|| code=$?" in text, name
        assert "-eq 3" in text, f"{name} compares the exit code with 3"
