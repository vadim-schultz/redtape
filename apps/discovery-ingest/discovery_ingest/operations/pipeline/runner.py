"""Run the pipeline's phases: each one plans from fresh facts, runs its stages side by side, and ends before the next starts."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace

import httpx

from discovery_ingest.client.errors import DiscoveryMachineApiError
from discovery_ingest.operations.pipeline.deadline import RUN_CEILING_SECONDS, stage_seconds
from discovery_ingest.operations.pipeline.outcome import RunResult, StageOutcome
from discovery_ingest.operations.pipeline.plan import PlanFacts, PlannedStage, build_plan
from discovery_ingest.operations.pipeline.process import Spawner, collect_output, parse_report
from discovery_ingest.operations.pipeline.report import PipelineReport, build_report
from discovery_ingest.operations.pipeline.signals import StageRegistry
from discovery_ingest.operations.pipeline.stages import PHASES, Phase, stage_by_id


@dataclass(frozen=True, slots=True)
class PipelinePorts:
    """What a run takes from its caller: the plan reads, the process starter, the clock, the signal registry and the sink."""

    read_facts: Callable[[], PlanFacts]
    spawn: Spawner
    clock: Callable[[], float]
    registry: StageRegistry
    publish: Callable[[PipelineReport], None]


@dataclass(frozen=True, slots=True)
class RunContext:
    """What the phases of one run need: the plan reads, the deadline, the clock, the running processes and the starter."""

    read_facts: Callable[[], PlanFacts]
    deadline_at: float
    clock: Callable[[], float]
    registry: StageRegistry
    spawn: Spawner


def run_pipeline(ports: PipelinePorts) -> PipelineReport:
    """Run the phases in order, publish the report once, and return it."""
    started = ports.clock()
    ctx = RunContext(
        read_facts=ports.read_facts,
        deadline_at=started + RUN_CEILING_SECONDS,
        clock=ports.clock,
        registry=ports.registry,
        spawn=ports.spawn,
    )
    with ports.registry.handlers():
        result = _run_phases(ctx)
    report = build_report(
        result,
        elapsed_seconds=ports.clock() - started,
        ceiling_seconds=RUN_CEILING_SECONDS,
        interrupted=ports.registry.stopping,
    )
    ports.publish(report)
    return report


def run_phase(stages: Sequence[PlannedStage], ctx: RunContext) -> list[StageOutcome]:
    """Run ``stages`` side by side and return their outcomes in the order given; one that fails does not stop the rest."""
    if not stages:
        return []
    with ThreadPoolExecutor(max_workers=len(stages)) as pool:
        futures = [pool.submit(_run_one, stage, ctx) for stage in stages]
        return [future.result() for future in futures]


def _run_phases(ctx: RunContext) -> RunResult:
    """Run each phase in turn; a ledger error or a stop ends the run before the next phase."""
    result = RunResult()
    for phase in PHASES:
        result = _run_one_phase(ctx, result, phase)
        if result.ledger_error is not None or ctx.registry.stopping:
            break
    return result


def _run_one_phase(ctx: RunContext, result: RunResult, phase: Phase) -> RunResult:
    """Plan one phase from fresh facts and run it; a ledger that cannot be read starts no stage of it."""
    try:
        facts = ctx.read_facts()
    except (DiscoveryMachineApiError, httpx.HTTPError) as err:
        return replace(result, ledger_error=str(err))
    plan = build_plan(facts, {stage: phase.number for stage in phase.stage_ids})
    outcomes = run_phase(plan.stages, ctx)
    return replace(
        result,
        outcomes=(*result.outcomes, *outcomes),
        omitted=(*result.omitted, *plan.omitted),
    )


def _run_one(stage: PlannedStage, ctx: RunContext) -> StageOutcome:
    """Start one stage with the time left to the deadline, or record why it did not start."""
    seconds = stage_seconds(ctx.deadline_at, ctx.clock())
    if ctx.registry.stopping:
        return _not_started(stage, "stopped")
    if seconds is None:
        return _not_started(stage, "deadline")
    return _execute(stage, seconds, ctx)


def _spawn_failed(stage: PlannedStage, err: OSError) -> StageOutcome:
    """Return the outcome of a stage whose process could not be started: a failure that names the error type."""
    name = type(err).__name__
    return StageOutcome(
        stage=stage.stage,
        phase=stage.phase,
        started=False,
        time_budget_seconds=None,
        note=f"could not start: {name}: {err}",
        spawn_error=name,
    )


def _not_started(stage: PlannedStage, note: str) -> StageOutcome:
    """Return the outcome of a stage that was not started, with the reason."""
    return StageOutcome(stage=stage.stage, phase=stage.phase, started=False, time_budget_seconds=None, note=note)


def _execute(stage: PlannedStage, seconds: float, ctx: RunContext) -> StageOutcome:
    """Run the stage's process under its budget, and return the outcome with the report it printed."""
    try:
        process = ctx.spawn(stage_by_id(stage.stage).argv(stage.caps, seconds))
    except OSError as err:
        return _spawn_failed(stage, err)
    ctx.registry.admit(process)
    try:
        stdout = collect_output(process, seconds)
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
