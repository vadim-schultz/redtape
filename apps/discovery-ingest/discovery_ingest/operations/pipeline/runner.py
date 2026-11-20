"""Run the stages of one phase as subprocesses, forward SIGTERM and SIGINT to them, and read each stage's report."""

from __future__ import annotations

import signal
import subprocess
import sys
import threading
from collections.abc import Callable, Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from types import FrameType
from typing import Protocol

from pydantic import ValidationError

from discovery_ingest.operations.pipeline.deadline import stage_seconds
from discovery_ingest.operations.pipeline.plan import PlannedStage
from discovery_ingest.operations.pipeline.stages import stage_by_id
from discovery_ingest.schemas import DrainReport

GRACE_SECONDS = 180.0
"""How long past its own budget a stage may run before it is sent SIGTERM and its report is read as it stands."""


class StageProcess(Protocol):
    """The part of a started process the runner uses: wait for its output, read its exit code, signal it."""

    returncode: int | None

    def communicate(self, timeout: float | None = None) -> tuple[str | None, str | None]:
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


class StageRegistry:
    """The stage processes that are running and whether a stop signal has arrived.

    A stop is forwarded to every process running at the time and to any process admitted after it.
    """

    def __init__(self) -> None:
        """Start with no process running and no stop."""
        self._lock = threading.Lock()
        self._live: set[StageProcess] = set()
        self._signum: int | None = None

    @property
    def stopping(self) -> bool:
        """Return whether a stop signal has arrived."""
        return self._signum is not None

    def admit(self, process: StageProcess) -> None:
        """Count ``process`` as running; if a stop has already arrived, forward it to the process at once."""
        with self._lock:
            if self._signum is not None:
                process.send_signal(self._signum)
            self._live.add(process)

    def release(self, process: StageProcess) -> None:
        """Stop counting ``process`` as running."""
        with self._lock:
            self._live.discard(process)

    def stop(self, signum: int) -> None:
        """Record the stop and forward ``signum`` to every running process."""
        with self._lock:
            self._signum = signum
            for process in self._live:
                process.send_signal(signum)

    @contextmanager
    def handlers(self) -> Iterator[None]:
        """Forward SIGTERM and SIGINT to the stages for the length of the block; off the main thread, nothing is installed."""
        if threading.current_thread() is not threading.main_thread():
            yield
            return
        previous = {signum: signal.signal(signum, self._on_signal) for signum in (signal.SIGTERM, signal.SIGINT)}
        try:
            yield
        finally:
            _restore(previous)

    def _on_signal(self, signum: int, _frame: FrameType | None) -> None:
        """Forward the signal the process received."""
        self.stop(signum)


def _restore(previous: dict[int, signal._HANDLER]) -> None:
    """Put back the handlers that were installed before :meth:`StageRegistry.handlers`, where Python knows them."""
    for signum, handler in previous.items():
        if handler is not None:
            signal.signal(signum, handler)


@dataclass(frozen=True, slots=True)
class StageOutcome:
    """What one stage did in its phase: whether it started, its budget, its exit code and the report it printed."""

    stage: str
    phase: int
    started: bool
    time_budget_seconds: float | None
    exit_code: int | None = None
    report: DrainReport | None = None
    note: str = ""

    @property
    def failed(self) -> bool:
        """Return whether a started stage failed: no report, a report of failure, or a non-zero exit."""
        if not self.started:
            return False
        return self.report is None or not self.report.succeeded or self.exit_code != 0


@dataclass(frozen=True, slots=True)
class RunContext:
    """What a phase needs to run its stages: the deadline, the clock, the running processes and how to start one."""

    deadline_at: float
    clock: Callable[[], float]
    registry: StageRegistry
    spawn: Spawner


def run_phase(stages: Sequence[PlannedStage], ctx: RunContext) -> list[StageOutcome]:
    """Run ``stages`` side by side and return their outcomes in the order given; one that fails does not stop the rest."""
    if not stages:
        return []
    with ThreadPoolExecutor(max_workers=len(stages)) as pool:
        futures = [pool.submit(_run_one, stage, ctx) for stage in stages]
        return [future.result() for future in futures]


def _run_one(stage: PlannedStage, ctx: RunContext) -> StageOutcome:
    """Start one stage with the time left to the deadline, or record why it did not start."""
    seconds = stage_seconds(ctx.deadline_at, ctx.clock())
    if ctx.registry.stopping:
        return _not_started(stage, "stopped")
    if seconds is None:
        return _not_started(stage, "deadline")
    return _execute(stage, seconds, ctx)


def _not_started(stage: PlannedStage, note: str) -> StageOutcome:
    """Return the outcome of a stage that was not started, with the reason."""
    return StageOutcome(stage=stage.stage, phase=stage.phase, started=False, time_budget_seconds=None, note=note)


def _execute(stage: PlannedStage, seconds: float, ctx: RunContext) -> StageOutcome:
    """Run the stage's process under its budget, and return the outcome with the report it printed."""
    process = ctx.spawn(stage_by_id(stage.stage).argv(stage.caps, seconds))
    ctx.registry.admit(process)
    try:
        stdout = _collect(process, seconds)
    finally:
        ctx.registry.release(process)
    return StageOutcome(
        stage=stage.stage,
        phase=stage.phase,
        started=True,
        time_budget_seconds=seconds,
        exit_code=process.returncode,
        report=parse_report(stdout),
    )


def _collect(process: StageProcess, seconds: float) -> str | None:
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
