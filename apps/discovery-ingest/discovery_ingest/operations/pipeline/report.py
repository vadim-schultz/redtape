"""The run's report: one record per stage, what the run was held to, and the markdown summary for the job page."""

from __future__ import annotations

from pydantic import BaseModel

from discovery_ingest.operations.pipeline.plan import OmittedStage


class StageRecord(BaseModel):
    """What one stage did: whether it started and succeeded, its budget, and what its drain report counted."""

    stage: str
    phase: int
    started: bool
    succeeded: bool
    note: str = ""
    time_budget_seconds: float | None = None
    exit_code: int | None = None
    stop_reason: str | None = None
    claimed: int = 0
    completed: int = 0
    failed: int = 0
    browser_seconds_used: float = 0.0
    neurons_used: float = 0.0
    characters_used: int = 0


class PipelineReport(BaseModel):
    """The whole run: whether it succeeded, whether a signal stopped it, the ledger error if any, its time and each stage."""

    succeeded: bool
    interrupted: bool
    ledger_error: str | None
    elapsed_seconds: float
    ceiling_seconds: float
    omitted: list[OmittedStage]
    stages: list[StageRecord]


def publish_to_step_summary(report: PipelineReport, *, path: str | None) -> None:
    """Leave the summary unwritten, as a placeholder until it is implemented."""
    del report, path
