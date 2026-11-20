"""The run's report: one record per stage, the minutes the run spent, and the markdown summary for the job page."""

from __future__ import annotations

import os
from collections.abc import Sequence

from pydantic import BaseModel

from discovery_ingest.operations.pipeline.plan import OmittedStage
from discovery_ingest.operations.pipeline.runner import StageOutcome


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
    """The whole run: whether it succeeded, whether a signal stopped it, its time and minutes, and each stage."""

    succeeded: bool
    interrupted: bool
    elapsed_seconds: float
    run_seconds: float
    minutes_reported: int
    minutes_recorded: bool
    omitted: list[OmittedStage]
    stages: list[StageRecord]


def minutes_for(elapsed_seconds: float) -> int:
    """Return the Actions minutes a run is billed: its elapsed time rounded up, plus one for runner setup and rounding."""
    return int((elapsed_seconds + 59) // 60) + 1


def stage_record(outcome: StageOutcome) -> StageRecord:
    """Return the record of one stage outcome, with the counts of its report when it printed one."""
    report = outcome.report
    return StageRecord(
        stage=outcome.stage,
        phase=outcome.phase,
        started=outcome.started,
        succeeded=not outcome.failed,
        note=outcome.note,
        time_budget_seconds=outcome.time_budget_seconds,
        exit_code=outcome.exit_code,
        stop_reason=None if report is None else report.stop_reason,
        claimed=0 if report is None else report.claimed,
        completed=0 if report is None else report.completed,
        failed=0 if report is None else report.failed,
        browser_seconds_used=0.0 if report is None else report.browser_seconds_used,
        neurons_used=0.0 if report is None else report.neurons_used,
        characters_used=0 if report is None else report.characters_used,
    )


def build_report(
    outcomes: Sequence[StageOutcome],
    omitted: Sequence[OmittedStage],
    *,
    elapsed_seconds: float,
    run_seconds: float,
    interrupted: bool,
    minutes: int,
    recorded: bool,
) -> PipelineReport:
    """Return the run's report: it succeeds only when no signal stopped it and no started stage failed."""
    return PipelineReport(
        succeeded=not interrupted and not any(outcome.failed for outcome in outcomes),
        interrupted=interrupted,
        elapsed_seconds=elapsed_seconds,
        run_seconds=run_seconds,
        minutes_reported=minutes,
        minutes_recorded=recorded,
        omitted=list(omitted),
        stages=[stage_record(outcome) for outcome in outcomes],
    )


def render_summary(report: PipelineReport) -> str:
    """Return the run as markdown: one row per stage, then what was left out and what the run cost."""
    lines = [
        "### Discovery pipeline",
        "",
        "| phase | stage | started | succeeded | stop reason | claimed | completed | failed | note |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    lines += [_row(record) for record in report.stages]
    lines += [
        "",
        f"Run budget {report.run_seconds:.0f} s, used {report.elapsed_seconds:.0f} s. "
        f"Actions minutes reported: {report.minutes_reported} "
        f"({'recorded' if report.minutes_recorded else 'ledger unreachable'}).",
        f"Interrupted: {'yes' if report.interrupted else 'no'}. Succeeded: {'yes' if report.succeeded else 'no'}.",
    ]
    if report.omitted:
        lines.append("Left out: " + ", ".join(f"{item.stage} ({item.reason})" for item in report.omitted))
    return "\n".join(lines) + "\n"


def _row(record: StageRecord) -> str:
    """Return the markdown row of one stage."""
    cells = [
        str(record.phase),
        record.stage,
        "yes" if record.started else "no",
        "yes" if record.succeeded else "no",
        record.stop_reason or "",
        str(record.claimed),
        str(record.completed),
        str(record.failed),
        record.note,
    ]
    return "| " + " | ".join(cells) + " |"


def publish_to_step_summary(report: PipelineReport) -> None:
    """Append the markdown summary to ``GITHUB_STEP_SUMMARY`` when the job has one; nothing happens elsewhere."""
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(render_summary(report))
