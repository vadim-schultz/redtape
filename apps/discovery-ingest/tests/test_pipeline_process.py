"""Waiting for one stage process: SIGTERM after its budget, then SIGKILL when it ignores SIGTERM (chapter 12)."""

from __future__ import annotations

import signal
import subprocess

from discovery_ingest.operations.pipeline.process import collect_output


class PoliteStage:
    """A stage that stops on SIGTERM and prints its report as it does."""

    def __init__(self) -> None:
        """Start running, with no signal received."""
        self.returncode: int | None = None
        self.signals: list[int] = []

    def communicate(self, input: str | None = None, timeout: float | None = None) -> tuple[str | None, str | None]:
        """Time out while running; once SIGTERM has arrived, finish with a report."""
        if signal.SIGTERM not in self.signals:
            raise subprocess.TimeoutExpired("stage", timeout or 0.0)
        self.returncode = -signal.SIGTERM
        return '{"claimed": 0}', None

    def send_signal(self, signum: int) -> None:
        """Record the signal."""
        self.signals.append(signum)


class StubbornStage:
    """A stage that ignores SIGTERM and dies only to SIGKILL."""

    def __init__(self) -> None:
        """Start running, with no signal received."""
        self.returncode: int | None = None
        self.signals: list[int] = []

    def communicate(self, input: str | None = None, timeout: float | None = None) -> tuple[str | None, str | None]:
        """Time out while alive; a bounded wait is needed, so an unbounded one would hang the test."""
        if signal.SIGKILL in self.signals:
            self.returncode = -signal.SIGKILL
            return None, None
        if timeout is None:
            raise AssertionError("an unbounded wait before SIGKILL would hang the run")
        raise subprocess.TimeoutExpired("stage", timeout)

    def send_signal(self, signum: int) -> None:
        """Record the signal."""
        self.signals.append(signum)


def test_a_stage_that_stops_on_sigterm_is_read_as_it_stands_without_a_kill() -> None:
    stage = PoliteStage()

    stdout = collect_output(stage, seconds=60.0)

    assert stdout == '{"claimed": 0}'
    assert stage.signals == [signal.SIGTERM]


def test_a_stage_that_ignores_sigterm_is_killed_after_the_second_grace() -> None:
    stage = StubbornStage()

    stdout = collect_output(stage, seconds=60.0)

    assert stdout is None
    assert stage.signals == [signal.SIGTERM, signal.SIGKILL]
    assert stage.returncode == -signal.SIGKILL
