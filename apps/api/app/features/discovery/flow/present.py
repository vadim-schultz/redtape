"""Shape the flow's domain values into the response models the admin route serves."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from app.features.discovery.budgets import BudgetStatus
from app.features.discovery.flow.reads import Intake, LastRun
from app.features.discovery.flow.stage import Edge, Stage
from app.features.discovery.flow.state import StageFacts, StageState
from app.schema.discovery.flow import (
    FlowAllotmentRead,
    FlowEdgeRead,
    FlowHeadroomRead,
    FlowLastRunRead,
    FlowStageRead,
)


def last_run_read(run: LastRun | None) -> FlowLastRunRead | None:
    """Return the response form of ``run``, or ``None`` when the stage has no recorded run."""
    if run is None:
        return None
    return FlowLastRunRead(
        status=run.status.value, stop_reason=run.stop_reason, started_at=run.started_at, finished_at=run.finished_at
    )


@dataclass(frozen=True, slots=True)
class StageView:
    """One stage as the response shows it: its definition, its state, its facts and its newest run."""

    stage: Stage
    state: StageState
    facts: StageFacts
    run: LastRun | None


def stage_read(view: StageView) -> FlowStageRead:
    """Return the response form of one stage with its state, its ready work and its last run."""
    return FlowStageRead(
        id=view.stage.id,
        label=view.stage.label,
        state=view.state.value,
        ready=view.facts.ready,
        failed_24h=view.facts.failed_24h,
        last_run=last_run_read(view.run),
    )


def edge_read(edge: Edge, intake: Mapping[str, Intake]) -> FlowEdgeRead:
    """Return the response form of ``edge``; its count is the intake of the stage it feeds."""
    return FlowEdgeRead.model_validate(
        {
            "from": edge.source,
            "to": edge.target,
            "tasks_created_24h": intake[edge.target].created_24h,
            "manual_only": edge.manual_only,
        }
    )


def allotment_read(status: BudgetStatus, spent: Mapping[str, float]) -> FlowAllotmentRead:
    """Return the response form of one allotment with the spend of the last day by run stage."""
    return FlowAllotmentRead(
        resource=status.resource.value, used=float(status.used), cap=status.cap, spent_by_stage=dict(spent)
    )


def unused_headroom_reads(stages: Sequence[Stage], facts: Mapping[str, StageFacts]) -> list[FlowHeadroomRead]:
    """Return one entry per stage with ready work whose allotment still has headroom above the unused share."""
    return [
        FlowHeadroomRead(resource=stage.allotment.value, stage=stage.id)
        for stage in stages
        if stage.allotment is not None and facts[stage.id].has_headroom and facts[stage.id].has_ready_work
    ]
