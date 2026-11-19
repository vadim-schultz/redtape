"""Response models for the admin pipeline flow route."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

FlowStageState = Literal[
    "dead",
    "budget_stopped",
    "throttled",
    "blocked",
    "starved",
    "overdue",
    "backlogged",
    "flowing",
    "idle",
]
"""The stage states, named as ``app.features.discovery.flow.state.StageState`` names them."""

FlowResource = Literal[
    "r2_class_a",
    "r2_class_b",
    "browser_seconds",
    "neurons",
    "actions_minutes",
    "azure_translator_chars",
]
"""The budget resources, named as ``app.features.discovery.budget_resources.BudgetResource`` names them."""


class FlowLastRunRead(BaseModel):
    """The newest run of a stage's run stage."""

    status: Literal["running", "succeeded", "failed"]
    stop_reason: str | None
    started_at: datetime
    finished_at: datetime | None


class FlowStageRead(BaseModel):
    """One stage: its state, its ready work, the tasks it failed in the last day and its last run."""

    id: str
    label: str
    state: FlowStageState
    ready: int
    failed_24h: int
    last_run: FlowLastRunRead | None


class FlowEdgeRead(BaseModel):
    """One edge: how many tasks its target took in the last day, and whether an operator command alone feeds it."""

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    from_stage: str = Field(alias="from")
    to: str
    tasks_created_24h: int
    manual_only: bool


class FlowAllotmentRead(BaseModel):
    """One allotment: its use in the current period, its cap and the spend of the last day by run stage."""

    resource: FlowResource
    used: float
    cap: int
    spent_by_stage: dict[str, float]


class FlowHeadroomRead(BaseModel):
    """Unused headroom: a stage with ready work draws on an allotment with room left."""

    resource: FlowResource
    stage: str


class FlowResponse(BaseModel):
    """The whole pipeline flow: stages, edges, allotments and the unused headroom that waits for work."""

    stages: list[FlowStageRead]
    edges: list[FlowEdgeRead]
    allotments: list[FlowAllotmentRead]
    unused_headroom: list[FlowHeadroomRead]
