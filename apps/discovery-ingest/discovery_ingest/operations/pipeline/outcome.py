"""What one stage did in its phase, and what the whole run of the phases returned."""

from __future__ import annotations

from dataclasses import dataclass

from discovery_ingest.operations.pipeline.plan import OmittedStage
from discovery_ingest.schemas import DrainReport


@dataclass(frozen=True, slots=True)
class StageOutcome:
    """What one stage did in its phase: whether it started, its budget, its exit code and the report it printed."""

    stage: str
    phase: int
    started: bool
    time_budget_seconds: float | None
    exit_code: int | None = None
    report: DrainReport | None = None
    note: str = ""

    @property
    def failed(self) -> bool:
        """Return whether a started stage failed: no report, a report of failure, or a non-zero exit."""
        if not self.started:
            return False
        return self.report is None or not self.report.succeeded or self.exit_code != 0


@dataclass(frozen=True, slots=True)
class RunResult:
    """What the phases did: each stage's outcome, the stages each plan left out, and the ledger error that ended the run."""

    outcomes: tuple[StageOutcome, ...] = ()
    omitted: tuple[OmittedStage, ...] = ()
    ledger_error: str | None = None
