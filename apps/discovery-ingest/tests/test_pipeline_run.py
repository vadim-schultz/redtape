"""The pipeline run: three phases of subprocesses, failure isolation, the deadline, signals and one report (chapter 12)."""

from __future__ import annotations

import signal
from collections.abc import Callable
from dataclasses import dataclass, field

from discovery_ingest.operations.pipeline import (
    PipelinePorts,
    PipelineReport,
    PlanFacts,
    StageRecord,
    StageRegistry,
    run_pipeline,
)

from pipeline_fakes import Behaviour, FakeSpawner, report_line


class FakeClock:
    """A clock in seconds that a test moves by hand."""

    def __init__(self, now: float = 0.0) -> None:
        """Start at ``now``."""
        self.now = now

    def __call__(self) -> float:
        """Return the current instant."""
        return self.now


@dataclass
class Recorder:
    """Counts the budget calls and keeps the published reports."""

    minutes: list[int] = field(default_factory=list)
    published: list[PipelineReport] = field(default_factory=list)

    def record_minutes(self, minutes: int) -> bool:
        """Remember the minutes a call reports; the ledger is always reachable here."""
        self.minutes.append(minutes)
        return True

    def publish(self, report: PipelineReport) -> None:
        """Remember the report that was published."""
        self.published.append(report)


def facts(ready: dict[str, int], *, actions: float = 600.0, days: int = 10) -> PlanFacts:
    """Return facts with ``ready`` work per stage, ample headroom, and ``actions`` minutes over ``days`` days."""
    return PlanFacts(
        ready=ready,
        headroom={"browser_seconds": 570.0, "neurons": 8500.0},
        actions_minutes_remaining=actions,
        days_left=days,
    )


def make_ports(
    spawner: FakeSpawner,
    read_facts: Callable[[], PlanFacts],
    *,
    clock: FakeClock | None = None,
    registry: StageRegistry | None = None,
    recorder: Recorder | None = None,
) -> PipelinePorts:
    """Wire the fakes into the ports a run takes."""
    recorded = recorder or Recorder()
    return PipelinePorts(
        read_facts=read_facts,
        spawn=spawner,
        clock=clock or FakeClock(),
        record_minutes=recorded.record_minutes,
        publish=recorded.publish,
        registry=registry or StageRegistry(),
    )


def record_of(report: PipelineReport, stage: str) -> StageRecord:
    """Return the first record of ``stage`` in ``report``."""
    return next(record for record in report.stages if record.stage == stage)


def test_phase_two_starts_only_after_phase_one_ends() -> None:
    spawner = FakeSpawner()

    run_pipeline(make_ports(spawner, lambda: facts({"seed": 5, "llm": 5})))

    assert spawner.events.index("end:seed") < spawner.events.index("start:llm")


def test_a_failing_stage_does_not_stop_the_other_stages() -> None:
    failing = Behaviour(stdout=report_line(succeeded=False, stop_reason="error"), exit_code=1)
    spawner = FakeSpawner({"render": failing})

    report = run_pipeline(make_ports(spawner, lambda: facts({"render": 5, "seed": 5, "llm": 5})))

    assert {"seed", "llm"} <= set(spawner.started())
    assert record_of(report, "render").succeeded is False
    assert record_of(report, "llm").succeeded is True
    assert report.succeeded is False


def test_a_stage_that_prints_no_report_counts_as_failed() -> None:
    crashed = Behaviour(stdout="Traceback (most recent call last): boom", exit_code=2)
    spawner = FakeSpawner({"embed": crashed})

    report = run_pipeline(make_ports(spawner, lambda: facts({"embed": 5})))

    assert record_of(report, "embed").succeeded is False
    assert report.succeeded is False


def test_the_deadline_gives_each_stage_the_time_left_capped_and_skips_one_with_under_a_minute_left() -> None:
    clock = FakeClock()
    reads = iter([(0.0, facts({"seed": 5, "embed": 5})), (2000.0, facts({"llm": 5})), (2950.0, facts({"seed": 5}))])

    def read_facts() -> PlanFacts:
        at, value = next(reads)
        clock.now = at
        return value

    spawner = FakeSpawner()
    report = run_pipeline(make_ports(spawner, read_facts, clock=clock, registry=StageRegistry()))

    budgets = {process.stage: process.budget_seconds() for process in spawner.processes}
    assert budgets == {"seed": 1200.0, "embed": 1200.0, "llm": 1000.0}
    assert [record.started for record in report.stages if record.phase == 3] == [False]
    assert len(spawner.processes) == 3


def test_sigterm_forwards_to_the_running_stage_and_closes_the_run_without_starting_another() -> None:
    registry = StageRegistry()
    stopping = Behaviour(stdout=None, exit_code=1, on_wait=lambda: registry.stop(signal.SIGTERM))
    spawner = FakeSpawner({"seed": stopping})
    recorder = Recorder()

    report = run_pipeline(
        make_ports(spawner, lambda: facts({"seed": 5, "llm": 5}), registry=registry, recorder=recorder)
    )

    assert spawner.process("seed").signals == [signal.SIGTERM]
    assert "start:llm" not in spawner.events
    assert report.interrupted is True
    assert report.succeeded is False
    assert recorder.minutes == [report.minutes_reported]


def test_the_budget_report_is_called_once_with_the_minutes_of_the_run() -> None:
    recorder = Recorder()

    report = run_pipeline(make_ports(FakeSpawner(), lambda: facts({"seed": 5, "llm": 5}), recorder=recorder))

    assert len(recorder.minutes) == 1
    assert recorder.minutes == [report.minutes_reported]
    assert report.minutes_reported >= 1
    assert recorder.published == [report]
