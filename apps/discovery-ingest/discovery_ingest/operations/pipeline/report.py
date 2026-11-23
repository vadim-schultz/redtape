"""The run's report: one record per stage, what the run was held to, and the markdown summary for the job page."""

from __future__ import annotations

from pydantic import BaseModel

from discovery_ingest.operations.pipeline.outcome import RunResult, StageOutcome
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


def stage_record(outcome: StageOutcome) -> StageRecord:
    """Return the record of one stage outcome, with the counts of its report when it printed one."""
    report = outcome.report
    return StageRecord(
        stage=outcome.stage,
        phase=outcome.phase,
        started=outcome.started,
        succeeded=outcome.started and not outcome.failed,
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
    result: RunResult,
    *,
    elapsed_seconds: float,
    ceiling_seconds: float,
    interrupted: bool,
) -> PipelineReport:
    """Return the run's report: it succeeds only when no signal stopped it, the ledger was read and no started stage failed."""
    failed = any(outcome.failed for outcome in result.outcomes)
    return PipelineReport(
        succeeded=not interrupted and result.ledger_error is None and not failed,
        interrupted=interrupted,
        ledger_error=result.ledger_error,
        elapsed_seconds=elapsed_seconds,
        ceiling_seconds=ceiling_seconds,
        omitted=list(result.omitted),
        stages=[stage_record(outcome) for outcome in result.outcomes],
    )


def render_summary(report: PipelineReport) -> str:
    """Return the run as markdown: one row per stage, then the ceiling, the outcome and what was left out."""
    lines = [
        "### Discovery pipeline",
        "",
        "| phase | stage | started | succeeded | stop reason | claimed | completed | failed | note |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    lines += [_row(record) for record in report.stages]
    lines += [
        "",
        f"Ceiling {report.ceiling_seconds:.0f} s, used {report.elapsed_seconds:.0f} s. "
        f"Interrupted: {'yes' if report.interrupted else 'no'}. Succeeded: {'yes' if report.succeeded else 'no'}.",
    ]
    if report.ledger_error is not None:
        lines.append(f"Ledger unreadable, no stage was started: {report.ledger_error}")
    if report.omitted:
        lines.append(
            "Left out: " + ", ".join(f"{item.stage} phase {item.phase} ({item.reason})" for item in report.omitted)
        )
    return "\n".join(lines) + "\n"


def _row(record: StageRecord) -> str:
    """Return the markdown row of one stage."""
    cells = [
        str(record.phase),
        record.stage,
        "yes" if record.started else "no",
        ("yes" if record.succeeded else "no") if record.started else "",
        record.stop_reason or "",
        str(record.claimed),
        str(record.completed),
        str(record.failed),
        record.note,
    ]
    return "| " + " | ".join(cells) + " |"


def publish_to_step_summary(report: PipelineReport, *, path: str | None) -> None:
    """Append the markdown summary to ``path`` (the job's ``GITHUB_STEP_SUMMARY``); nothing is written without one."""
    if path is None:
        return
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(render_summary(report))
