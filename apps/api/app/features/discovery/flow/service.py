"""The admin view of the pipeline flow: every stage with its state, the edges, the allotments and the unused headroom."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.config import settings
from app.features.discovery.budget_resources import BudgetResource
from app.features.discovery.budgets import BudgetService, BudgetStatus
from app.features.discovery.flow.facts import StageReading, stage_facts, upstream_overdue
from app.features.discovery.flow.present import allotment_read, edge_read, stage_read, unused_headroom_reads
from app.features.discovery.flow.queues import QueueFigureReader
from app.features.discovery.flow.reads import NO_INTAKE, FlowReads, Intake, LastRun, sum_intakes
from app.features.discovery.flow.spend import spend_by_resource
from app.features.discovery.flow.stage import FlowQueue, Stage
from app.features.discovery.flow.state import StageFacts, classify_stage
from app.features.discovery.flow.thresholds import DEFAULT_THRESHOLDS
from app.features.discovery.flow.topology import EDGES, STAGES
from app.features.discovery.repository import DiscoveryRepository
from app.features.search.clock import Clock, utc_now
from app.models.discovery import DiscoveryTaskKind
from app.schema.discovery.flow import FlowResponse

LOOKBACK = timedelta(hours=24)
"""The window the intake, the spend and the 24 h counts are taken over."""


@dataclass(frozen=True, slots=True)
class _Gathered:
    """Everything one flow response is assembled from, read at one instant."""

    now: datetime
    runs: Mapping[str, LastRun]
    intake: Mapping[str, Intake]
    allotments: Mapping[BudgetResource, BudgetStatus]
    spend: Mapping[str, Mapping[str, float]]

    def last_run(self, stage: Stage) -> LastRun | None:
        """Return the newest run of the run stage that ``stage`` writes, if one was recorded."""
        return self.runs.get(stage.run_stage.value)


class FlowService:
    """Describe the pipeline from the stored queues, runs and budget ledger; it writes nothing."""

    def __init__(self, repository: DiscoveryRepository, budgets: BudgetService, clock: Clock = utc_now) -> None:
        """Bind the service to ``repository`` for the queues and runs, to ``budgets`` for the allotments and to ``clock``."""
        self._budgets = budgets
        self._clock = clock
        self._reads = FlowReads(repository.session)
        self._queues = QueueFigureReader(repository)

    def flow(self) -> FlowResponse:
        """Return every stage's state and last run, the edges, the allotments and the headroom that waits for work."""
        gathered = self._gather(self._clock())
        facts = {stage.id: self._facts(stage, gathered) for stage in STAGES}
        states = {stage.id: classify_stage(stage, facts[stage.id], DEFAULT_THRESHOLDS) for stage in STAGES}
        return FlowResponse(
            stages=[stage_read(stage, states[stage.id], facts[stage.id], gathered.last_run(stage)) for stage in STAGES],
            edges=[edge_read(edge, gathered.intake) for edge in EDGES],
            allotments=[
                allotment_read(status, gathered.spend.get(status.resource.value, {}))
                for status in gathered.allotments.values()
            ],
            unused_headroom=unused_headroom_reads(STAGES, facts),
        )

    def _gather(self, now: datetime) -> _Gathered:
        return _Gathered(
            now=now,
            runs=self._reads.latest_runs(),
            intake=self._stage_intake(now),
            allotments={status.resource: status for status in self._budgets.snapshot(now)},
            spend=spend_by_resource(self._reads.spend_since(now - LOOKBACK)),
        )

    def _stage_intake(self, now: datetime) -> dict[str, Intake]:
        since = now - LOOKBACK
        tasks = self._reads.task_intake(since)
        queues = self._reads.queue_intake(
            since, model=settings.embedding_model, locales=settings.translation_target_locale_codes
        )
        return {stage.id: _intake_of(stage, tasks, queues) for stage in STAGES}

    def _facts(self, stage: Stage, gathered: _Gathered) -> StageFacts:
        reading = StageReading(
            queue=self._queues.figures(stage, gathered.now),
            intake=gathered.intake[stage.id],
            last_run=gathered.last_run(stage),
            upstream_overdue=upstream_overdue(stage, gathered.runs, gathered.now, DEFAULT_THRESHOLDS),
            allotment=None if stage.allotment is None else gathered.allotments[stage.allotment],
        )
        return stage_facts(reading, gathered.now, DEFAULT_THRESHOLDS)


def _intake_of(stage: Stage, tasks: Mapping[DiscoveryTaskKind, Intake], queues: Mapping[FlowQueue, Intake]) -> Intake:
    if stage.queue is not None:
        return queues[stage.queue]
    return sum_intakes(tasks.get(kind, NO_INTAKE) for kind in stage.task_kinds)
