"""The plan: which stages have ready work now and what each may spend of its allotment. Pure: no I/O, no clock."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from pydantic import BaseModel, Field

from discovery_ingest.operations.pipeline.deadline import RUN_CEILING_SECONDS
from discovery_ingest.operations.pipeline.stages import FIRST_PASS, STAGES, StageSpec


@dataclass(frozen=True, slots=True)
class PlanFacts:
    """What the planner knows: the ready work per stage, the headroom of each allotment, and the stages that cannot run.

    ``headroom`` is what each allotment may still give after its reserve (the query-embedding floor for neurons).
    ``unconfigured`` names the stages that cannot run here (no model, no tail locales); they are omitted, not planned.
    """

    ready: Mapping[str, int]
    headroom: Mapping[str, float]
    unconfigured: frozenset[str] = frozenset()


class PlannedStage(BaseModel):
    """A stage with ready work, its phase, how many tasks it saw, and the caps it may spend."""

    stage: str
    phase: int
    ready: int
    caps: dict[str, float] = Field(default_factory=dict)


class OmittedStage(BaseModel):
    """A stage the plan left out, with the reason and the phase it would have run in."""

    stage: str
    phase: int
    reason: str


class PipelinePlan(BaseModel):
    """The stages to run, the stages left out, and the fixed ceiling the run is held to."""

    ceiling_seconds: float
    stages: list[PlannedStage]
    omitted: list[OmittedStage]


def build_plan(facts: PlanFacts, phases: Mapping[str, int] = FIRST_PASS) -> PipelinePlan:
    """Plan each stage named in ``phases`` (stage id to phase), in run order, from ``facts``."""
    grants = dict(facts.headroom)
    selected = [spec for spec in STAGES if spec.id in phases]
    outcomes = [_plan_one(spec, phases[spec.id], facts, grants) for spec in selected]
    planned = [item for item in outcomes if isinstance(item, PlannedStage)]
    omitted = [item for item in outcomes if isinstance(item, OmittedStage)]
    return PipelinePlan(ceiling_seconds=RUN_CEILING_SECONDS, stages=planned, omitted=omitted)


def _plan_one(spec: StageSpec, phase: int, facts: PlanFacts, grants: dict[str, float]) -> PlannedStage | OmittedStage:
    """Plan one stage, or say why it is left out; a granted cap comes off ``grants``."""
    if spec.id in facts.unconfigured:
        return OmittedStage(stage=spec.id, phase=phase, reason="not configured")
    ready = facts.ready.get(spec.id, 0)
    if ready <= 0:
        return OmittedStage(stage=spec.id, phase=phase, reason="no ready work")
    caps = _grant(spec, grants)
    if caps is None:
        return OmittedStage(stage=spec.id, phase=phase, reason="allotment short")
    return PlannedStage(stage=spec.id, phase=phase, ready=ready, caps=caps)


def _grant(spec: StageSpec, grants: dict[str, float]) -> dict[str, float] | None:
    """Return the cap ``spec`` may take from what is left, taking it off ``grants``; ``None`` below its floor."""
    if spec.resource is None:
        return {}
    granted = min(spec.cap, grants.get(spec.resource, 0.0))
    if granted < spec.floor:
        return None
    grants[spec.resource] = grants[spec.resource] - granted
    return {spec.resource: granted}
