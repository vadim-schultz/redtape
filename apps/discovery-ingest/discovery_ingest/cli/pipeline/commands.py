"""``pipeline``: plan the day's stages from the queue summaries and budgets, and run them in three phases."""

from __future__ import annotations

import typer

from discovery_ingest.cli.context import api_client, settings_of
from discovery_ingest.cli.errors import HELP_OPTIONS, fail, handles_api_errors, show_help_without_subcommand
from discovery_ingest.cli.pipeline.ports import live_ports, plan_context
from discovery_ingest.operations.pipeline import FIRST_PASS, build_plan, read_plan_facts, run_pipeline

ENABLED = "enabled"

pipeline_app = typer.Typer(
    name="pipeline",
    help="Daily pipeline: plan the stages, then run them in three phases",
    add_completion=False,
    pretty_exceptions_enable=False,
    rich_markup_mode=None,
    context_settings=HELP_OPTIONS,
)


@pipeline_app.callback(invoke_without_command=True)
def pipeline_group(ctx: typer.Context) -> None:
    """Daily pipeline: plan the stages, then run them in three phases."""
    show_help_without_subcommand(ctx)


@pipeline_app.command("plan")
@handles_api_errors("pipeline")
def pipeline_plan(ctx: typer.Context) -> None:
    """Print the stages with ready work and their caps as one JSON document."""
    plan = build_plan(read_plan_facts(api_client(ctx), plan_context(ctx)), FIRST_PASS)
    typer.echo(plan.model_dump_json())


@pipeline_app.command("run")
@handles_api_errors("pipeline")
def pipeline_run(ctx: typer.Context) -> None:
    """Run the stages in three phases; exit 1 when a stage failed, the run was stopped or the ledger was unreadable."""
    if settings_of(ctx).pipeline_orchestrator != ENABLED:
        typer.echo("PIPELINE_ORCHESTRATOR is not enabled; no stage was run", err=True)
        return
    report = run_pipeline(live_ports(ctx))
    if report.ledger_error is not None:
        fail(f"pipeline command failed: {report.ledger_error}")
    if not report.succeeded:
        raise typer.Exit(1)
