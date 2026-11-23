"""Start one stage as a subprocess, wait for it under its budget, and read the report it printed."""

from __future__ import annotations

import signal
import subprocess
import sys
from collections.abc import Callable, Sequence
from typing import Protocol

from pydantic import ValidationError

from discovery_ingest.schemas import DrainReport

GRACE_SECONDS = 180.0
"""How long past its own budget a stage may run before it is sent SIGTERM and its report is read as it stands."""


class StageProcess(Protocol):
    """The part of a started process the runner uses: wait for its output, read its exit code, signal it."""

    returncode: int | None

    def communicate(self, input: str | None = None, timeout: float | None = None) -> tuple[str | None, str | None]:
        """Wait for the process and return its stdout and stderr (stderr is not captured here)."""
        ...

    def send_signal(self, signum: int) -> None:
        """Send ``signum`` to the process."""
        ...


Spawner = Callable[[Sequence[str]], StageProcess]
"""Starts one stage from its arguments after ``python -m discovery_ingest``."""


def spawn_stage(argv: Sequence[str]) -> StageProcess:
    """Start ``python -m discovery_ingest`` with ``argv``; stdout is read for the report, stderr goes to the job log."""
    return subprocess.Popen([sys.executable, "-m", "discovery_ingest", *argv], stdout=subprocess.PIPE, text=True)


def collect_output(process: StageProcess, seconds: float) -> str | None:
    """Wait for the stage's output; past its budget plus the grace, send SIGTERM and read what it prints then."""
    try:
        stdout, _ = process.communicate(timeout=seconds + GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        process.send_signal(signal.SIGTERM)
        stdout, _ = process.communicate()
    return stdout


def parse_report(stdout: str | None) -> DrainReport | None:
    """Return the report a stage printed last on stdout, or ``None`` when its output holds no report."""
    lines = [line for line in (stdout or "").splitlines() if line.strip()]
    if not lines:
        return None
    try:
        return DrainReport.model_validate_json(lines[-1])
    except ValidationError:
        return None
