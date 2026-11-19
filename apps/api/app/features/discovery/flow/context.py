"""The inputs of one flow response: where the flow reads from, and what it read at one instant."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from app.features.discovery.artifact_read import ArtifactReadService
from app.features.discovery.budget_resources import BudgetResource
from app.features.discovery.budgets import BudgetService, BudgetStatus
from app.features.discovery.flow.reads import Intake, LastRun
from app.features.discovery.flow.stage import Stage
from app.features.discovery.repository import DiscoveryRepository


@dataclass(frozen=True, slots=True)
class FlowSources:
    """What the flow reads from: the discovery repository, the budget ledger and the artifact reads the page queue needs."""

    repository: DiscoveryRepository
    budgets: BudgetService
    artifacts: ArtifactReadService


@dataclass(frozen=True, slots=True)
class Gathered:
    """Everything one flow response is assembled from, read at one instant."""

    now: datetime
    runs: Mapping[str, LastRun]
    ages: Mapping[str, float | None]
    intake: Mapping[str, Intake]
    allotments: Mapping[BudgetResource, BudgetStatus]
    spend: Mapping[str, Mapping[str, float]]

    def last_run(self, stage: Stage) -> LastRun | None:
        """Return the newest run of the run stage that ``stage`` writes, if one was recorded."""
        return self.runs.get(stage.run_stage.value)

    def last_run_age(self, stage: Stage) -> float | None:
        """Return how many hours ago the newest run of ``stage``'s run stage started."""
        return self.ages.get(stage.run_stage.value)
