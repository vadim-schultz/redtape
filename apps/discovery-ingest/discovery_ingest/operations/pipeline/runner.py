"""Run the pipeline's phases as subprocesses (placeholder: starts no stage until the run is implemented)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from discovery_ingest.operations.pipeline.deadline import RUN_CEILING_SECONDS
from discovery_ingest.operations.pipeline.plan import PlanFacts
from discovery_ingest.operations.pipeline.process import Spawner
from discovery_ingest.operations.pipeline.report import PipelineReport
from discovery_ingest.operations.pipeline.signals import StageRegistry


@dataclass(frozen=True, slots=True)
class PipelinePorts:
    """What a run takes from its caller: the plan reads, the process starter, the clock, the signal registry and the sink."""

    read_facts: Callable[[], PlanFacts]
    spawn: Spawner
    clock: Callable[[], float]
    registry: StageRegistry
    publish: Callable[[PipelineReport], None]


def run_pipeline(ports: PipelinePorts) -> PipelineReport:
    """Report success, start no stage and publish nothing, as a placeholder."""
    del ports
    return PipelineReport(
        succeeded=True,
        interrupted=False,
        ledger_error=None,
        elapsed_seconds=0.0,
        ceiling_seconds=RUN_CEILING_SECONDS,
        omitted=[],
        stages=[],
    )
