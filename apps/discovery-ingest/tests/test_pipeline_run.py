"""The pipeline run: three phases of subprocesses, failure isolation, the deadline, signals and one summary (chapter 12)."""

from __future__ import annotations

import errno
import signal
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path

import httpx
from discovery_ingest.client.errors import DiscoveryMachineApiError
from discovery_ingest.operations.pipeline import (
    PipelinePorts,
    PipelineReport,
    PlanFacts,
    StageRecord,
    StageRegistry,
    publish_to_step_summary,
    run_pipeline,
)

from pipeline_fakes import Behaviour, FakeSpawner, report_line, stage_of


class FakeClock:
    """A clock in seconds that a test moves by hand."""

    def __init__(self, now: float = 0.0) -> None:
        """Start at ``now``."""
        self.now = now

    def __call__(self) -> float:
        """Return the current instant."""
        return self.now


@dataclass
class Published:
    """Keeps the reports the run published, in order."""

    reports: list[PipelineReport] = field(default_factory=list)

    def __call__(self, report: PipelineReport) -> None:
        """Remember one published report."""
        self.reports.append(report)


def facts(ready: dict[str, int]) -> PlanFacts:
    """Return facts with ``ready`` work per stage and ample headroom of browser seconds and neurons."""
    return PlanFacts(ready=ready, headroom={"browser_seconds": 570.0, "neurons": 8500.0})


def reads_in_order(
    *ready_per_read: dict[str, int], clock: FakeClock | None = None, at: Sequence[float] = ()
) -> Callable[[], PlanFacts]:
    """Return a plan read that answers call by call with the next ready work; later calls see no work.

    When ``clock`` and ``at`` are given, each call first moves the clock to the next instant in ``at``.
    """
    pending = list(ready_per_read)
    instants = list(at)

    def read() -> PlanFacts:
        if clock is not None and instants:
            clock.now = instants.pop(0)
        ready = pending.pop(0) if pending else {}
        return facts(ready)

    return read


def make_ports(
    spawner: FakeSpawner,
    read_facts: Callable[[], PlanFacts],
    *,
    clock: FakeClock | None = None,
    registry: StageRegistry | None = None,
    publish: Callable[[PipelineReport], None] | None = None,
) -> PipelinePorts:
    """Wire the fakes into the ports a run takes; the report goes to ``publish`` (a list of reports by default)."""
    return PipelinePorts(
        read_facts=read_facts,
        spawn=spawner,
        clock=clock or FakeClock(),
        registry=registry or StageRegistry(),
        publish=publish or Published(),
    )


def record_of(report: PipelineReport, stage: str) -> StageRecord:
    """Return the first record of ``stage`` in ``report``."""
    return next(record for record in report.stages if record.stage == stage)


def test_phase_two_starts_only_after_phase_one_ends() -> None:
    spawner = FakeSpawner()

    run_pipeline(make_ports(spawner, reads_in_order({"seed": 5}, {"llm": 5})))

    assert spawner.events.index("end:seed") < spawner.events.index("start:llm")


def test_a_failing_stage_does_not_stop_the_other_stages() -> None:
    failing = Behaviour(stdout=report_line(succeeded=False, stop_reason="error"), exit_code=1)
    spawner = FakeSpawner({"render": failing})

    report = run_pipeline(make_ports(spawner, reads_in_order({"render": 5, "seed": 5, "embed": 5})))

    assert {"seed", "embed"} <= set(spawner.started())
    assert record_of(report, "render").succeeded is False
    assert record_of(report, "seed").succeeded is True
    assert report.succeeded is False


def test_a_stage_that_prints_no_report_counts_as_failed() -> None:
    crashed = Behaviour(stdout="Traceback (most recent call last): boom", exit_code=2)
    spawner = FakeSpawner({"embed": crashed})

    report = run_pipeline(make_ports(spawner, reads_in_order({"embed": 5})))

    assert record_of(report, "embed").succeeded is False
    assert report.succeeded is False


def test_the_deadline_gives_each_stage_the_time_left_to_the_ceiling() -> None:
    clock = FakeClock()
    reads = reads_in_order({"seed": 5, "embed": 5}, {"llm": 5}, {"seed": 5}, clock=clock, at=[0.0, 2500.0, 3000.0])

    report = run_pipeline(make_ports(FakeSpawner(), reads, clock=clock))

    budgets = [(record.stage, record.phase, record.time_budget_seconds) for record in report.stages]
    assert budgets == [("seed", 1, 1200.0), ("embed", 1, 1200.0), ("llm", 2, 800.0), ("seed", 3, 300.0)]


def test_a_stage_is_not_started_with_less_than_a_minute_of_the_ceiling_left() -> None:
    clock = FakeClock()
    reads = reads_in_order({"seed": 5}, {}, {"seed": 5}, clock=clock, at=[0.0, 2000.0, 3260.0])
    spawner = FakeSpawner()

    report = run_pipeline(make_ports(spawner, reads, clock=clock))

    assert spawner.started() == ["seed"]
    final = [(record.stage, record.started, record.note) for record in report.stages if record.phase == 3]
    assert final == [("seed", False, "deadline")]


def test_a_final_pass_runs_a_stage_that_still_has_ready_work() -> None:
    spawner = FakeSpawner()

    report = run_pipeline(make_ports(spawner, reads_in_order({"seed": 5}, {}, {"seed": 3})))

    assert [(record.stage, record.phase) for record in report.stages] == [("seed", 1), ("seed", 3)]


def test_the_final_pass_does_not_run_a_stage_with_no_ready_work() -> None:
    spawner = FakeSpawner()

    report = run_pipeline(make_ports(spawner, reads_in_order({"seed": 5}, {}, {})))

    assert spawner.started() == ["seed"]
    assert [record.phase for record in report.stages] == [1]


def test_sigterm_closes_the_run_as_failed_and_starts_no_further_stage() -> None:
    registry = StageRegistry()
    stopping = Behaviour(stdout=None, exit_code=1, on_wait=lambda: registry.stop(signal.SIGTERM))
    spawner = FakeSpawner({"seed": stopping})
    published = Published()

    report = run_pipeline(
        make_ports(spawner, reads_in_order({"seed": 5}, {"llm": 5}, {"seed": 5}), registry=registry, publish=published)
    )

    assert spawner.process("seed").signals == [signal.SIGTERM]
    assert "start:llm" not in spawner.events
    assert report.interrupted is True
    assert report.succeeded is False
    assert published.reports == [report]


def test_the_run_summary_is_written_once_to_the_step_summary(tmp_path: Path) -> None:
    summary = tmp_path / "step-summary.md"

    run_pipeline(
        make_ports(
            FakeSpawner(),
            reads_in_order({"seed": 5}),
            publish=partial(publish_to_step_summary, path=str(summary)),
        )
    )

    assert summary.read_text(encoding="utf-8").count("### Discovery pipeline") == 1


def test_no_summary_is_written_without_a_step_summary_path(tmp_path: Path) -> None:
    report = run_pipeline(
        make_ports(FakeSpawner(), reads_in_order({"seed": 5}), publish=partial(publish_to_step_summary, path=None))
    )

    assert report.succeeded is True
    assert list(tmp_path.iterdir()) == []


def test_a_run_whose_ledger_cannot_be_read_starts_no_stage() -> None:
    spawner = FakeSpawner()

    def unreadable() -> PlanFacts:
        raise DiscoveryMachineApiError(500, "down")

    report = run_pipeline(make_ports(spawner, unreadable))

    assert spawner.started() == []
    assert report.ledger_error is not None
    assert report.succeeded is False


def test_an_unreachable_api_closes_the_run_as_failed_and_publishes_it_once() -> None:
    published = Published()

    def unreachable() -> PlanFacts:
        raise httpx.ConnectError("connection refused")

    report = run_pipeline(make_ports(FakeSpawner(), unreachable, publish=published))

    assert published.reports == [report]
    assert report.ledger_error is not None
    assert report.succeeded is False


def test_an_unreachable_api_starts_no_stage() -> None:
    spawner = FakeSpawner()

    def unreachable() -> PlanFacts:
        raise httpx.ConnectError("connection refused")

    run_pipeline(make_ports(spawner, unreachable))

    assert spawner.started() == []


def spawn_refusing(stage: str, spawner: FakeSpawner) -> Callable[[Sequence[str]], object]:
    """Return a starter that raises OSError for ``stage`` and starts every other stage through ``spawner``."""

    def spawn(argv: Sequence[str]) -> object:
        if stage_of(argv) == stage:
            raise OSError(errno.ENOEXEC, "Exec format error")
        return spawner(argv)

    return spawn


def test_a_stage_that_cannot_be_spawned_does_not_stop_the_other_stages() -> None:
    spawner = FakeSpawner()
    ports = PipelinePorts(
        read_facts=reads_in_order({"render": 5, "seed": 5}),
        spawn=spawn_refusing("render", spawner),  # type: ignore[arg-type]
        clock=FakeClock(),
        registry=StageRegistry(),
        publish=Published(),
    )

    report = run_pipeline(ports)

    assert "seed" in spawner.started()
    assert record_of(report, "seed").succeeded is True


def test_a_stage_that_cannot_be_spawned_fails_the_run_with_one_report_that_names_the_error() -> None:
    spawner = FakeSpawner()
    published = Published()
    ports = PipelinePorts(
        read_facts=reads_in_order({"render": 5, "seed": 5}),
        spawn=spawn_refusing("render", spawner),  # type: ignore[arg-type]
        clock=FakeClock(),
        registry=StageRegistry(),
        publish=published,
    )

    report = run_pipeline(ports)

    assert published.reports == [report]
    assert report.succeeded is False
    render = record_of(report, "render")
    assert render.started is False
    assert render.succeeded is False
    assert "OSError" in render.note
