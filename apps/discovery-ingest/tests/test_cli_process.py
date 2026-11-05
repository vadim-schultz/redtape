"""The real process: ``python -m discovery_ingest`` exit codes and streams, independent of ``main()``."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[1]


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("DISCOVERY_")}
    env["COLUMNS"] = "100"
    return subprocess.run(
        [sys.executable, "-m", "discovery_ingest", *args],
        cwd=APP,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def test_help_exits_0_with_usage_on_stdout() -> None:
    result = _run("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()
    assert result.stderr == ""


def test_a_bad_value_exits_2_with_error_on_stderr_and_nothing_on_stdout() -> None:
    result = _run("worker", "drain", "--max-tasks", "x")
    assert result.returncode == 2
    assert "error" in result.stderr.lower()
    assert result.stdout == ""


def test_fim_probe_with_a_bad_key_exits_2() -> None:
    result = _run("fim", "probe", "--keys", "1")
    assert result.returncode == 2
    assert result.stdout == ""


def test_budget_show_strict_without_api_settings_fails_with_nothing_on_stdout() -> None:
    result = _run("budget", "show", "--strict")
    assert result.returncode == 4
    assert result.stdout == ""


def test_budget_show_without_api_settings_warns_on_stderr_and_exits_0() -> None:
    result = _run("budget", "show")
    assert result.returncode == 0
    assert result.stdout == ""
    assert "budget ledger unreachable" in result.stderr


@pytest.mark.parametrize("argv", [[], ["worker"]], ids=["root", "group"])
def test_no_command_prints_help_to_stdout_and_exits_2(argv: list[str]) -> None:
    result = _run(*argv)
    assert result.returncode == 2
    assert "usage:" in result.stdout.lower()
