"""``budget``: the free-allocation ledger, read for a skip decision and written with the minutes a run spent."""

import json
from typing import Annotated

import typer

from discovery_ingest.cli.context import api_client
from discovery_ingest.cli.errors import HELP_OPTIONS, handles_api_errors, show_help_without_subcommand
from discovery_ingest.cli.options import budget_requirement, budget_resource, positive_minutes
from discovery_ingest.operations.budget import budget_view, record_minutes

EXIT_SHORT = 3
EXIT_LEDGER_UNAVAILABLE_STRICT = 4

budget_app = typer.Typer(
    name="budget",
    help="Free-allocation budget ledger",
    add_completion=False,
    pretty_exceptions_enable=False,
    rich_markup_mode=None,
    context_settings=HELP_OPTIONS,
)


@budget_app.callback(invoke_without_command=True)
def budget_group(ctx: typer.Context) -> None:
    """Free-allocation budget ledger."""
    show_help_without_subcommand(ctx)


@budget_app.command("show")
@handles_api_errors("budget")
def budget_show(
    ctx: typer.Context,
    resource: Annotated[
        list[str] | None, typer.Option("--resource", help="Only print this resource (repeatable)")
    ] = None,
    require_remaining: Annotated[
        list[str] | None,
        typer.Option(
            "--require-remaining",
            metavar="RESOURCE=N",
            help="Exit 3 when RESOURCE has less than N remaining or is exhausted (repeatable)",
        ),
    ] = None,
    strict: Annotated[
        bool, typer.Option("--strict", help="Exit 4 instead of 0 when the ledger is unreachable")
    ] = False,
) -> None:
    """Print the ledger; exit 3 when a required resource is short."""
    resources = [budget_resource(name) for name in resource or []]
    requirements = [budget_requirement(raw) for raw in require_remaining or []]
    view = budget_view(api_client(ctx), resources, requirements)
    if view is None:
        typer.echo("budget ledger unreachable; budgets were not checked", err=True)
        if strict:
            raise typer.Exit(EXIT_LEDGER_UNAVAILABLE_STRICT)
        return
    typer.echo(json.dumps({"items": [row.model_dump(mode="json") for row in view.rows]}))
    if view.short:
        typer.echo(f"budget short or exhausted: {', '.join(view.short)}", err=True)
        raise typer.Exit(EXIT_SHORT)


@budget_app.command("report-minutes")
@handles_api_errors("budget")
def budget_report_minutes(
    ctx: typer.Context,
    minutes: Annotated[int, typer.Option("--minutes", parser=positive_minutes)],
) -> None:
    """Add Actions minutes spent by this run to the ledger."""
    if not record_minutes(api_client(ctx), minutes):
        typer.echo("budget ledger unreachable; the minutes were not recorded", err=True)
