"""The types of the pipeline topology: a stage, an edge between two stages and the table-backed queues they read."""

from __future__ import annotations

import enum
from dataclasses import dataclass

from app.features.discovery.budget_resources import BudgetResource
from app.models.discovery import DiscoveryRunStage, DiscoveryTaskKind


class FlowQueue(enum.StrEnum):
    """The table-backed queues a stage reads, when it is not a discovery task kind."""

    EMBEDDING = "embedding"
    CARD_TRANSLATION = "card_translation"
    PAGE_TRANSLATION = "page_translation"


@dataclass(frozen=True, slots=True)
class Stage:
    """One step of the flow: the work it reads, the run stage it writes, the allotment it draws on and its cadence."""

    id: str
    label: str
    task_kinds: tuple[DiscoveryTaskKind, ...]
    queue: FlowQueue | None
    run_stage: DiscoveryRunStage
    allotment: BudgetResource | None
    cadence_hours: float


@dataclass(frozen=True, slots=True)
class Edge:
    """How one stage feeds another; ``manual_only`` marks an edge that exists only through an operator command."""

    source: str
    target: str
    manual_only: bool = False
