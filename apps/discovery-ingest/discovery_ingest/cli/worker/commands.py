"""``worker``: the discovery task worker and its drain."""

import json
from typing import Annotated

import typer

from discovery_ingest.cli.context import api_client, settings_of
from discovery_ingest.cli.errors import EXIT_FAILED, EXIT_USAGE, HELP_OPTIONS, fail, show_help_without_subcommand
from discovery_ingest.cli.options import task_kinds
from discovery_ingest.client import DiscoveryMachineApiError
from discovery_ingest.operations.drain import DrainOptions, run_drain
from discovery_ingest.schemas import WORKER_DEFAULT_TASK_KINDS
from discovery_ingest.worker.browser_setup import BrowserSetupError
from discovery_ingest.worker.llm_setup import LlmSetupError
from discovery_ingest.worker.policy import MAX_LLM_CONCURRENCY

worker_app = typer.Typer(
    name="worker",
    help="Discovery task worker",
    add_completion=False,
    pretty_exceptions_enable=False,
    rich_markup_mode=None,
    context_settings=HELP_OPTIONS,
)


@worker_app.callback(invoke_without_command=True)
def worker_group(ctx: typer.Context) -> None:
    """Discovery task worker."""
    show_help_without_subcommand(ctx)


@worker_app.command("drain")
def worker_drain(
    ctx: typer.Context,
    max_tasks: Annotated[
        int | None,
        typer.Option(
            "--max-tasks",
            help="Maximum tasks per claim request (1–50; default 50, or 5 when llm_extract is drained)",
        ),
    ] = None,
    max_batches: Annotated[
        int, typer.Option("--max-batches", help="Maximum claim/process batches (positive, default 1)")
    ] = 1,
    time_budget_seconds: Annotated[
        float | None,
        typer.Option("--time-budget-seconds", help="Optional positive wall-clock budget for the whole drain"),
    ] = None,
    browser_budget_seconds: Annotated[
        float,
        typer.Option(
            "--browser-budget-seconds",
            help="Browser seconds this run may spend on render_page and capture_screenshot (positive, default 570)",
        ),
    ] = 570.0,
    neuron_budget: Annotated[
        float | None,
        typer.Option(
            "--neuron-budget",
            help=(
                "Workers AI neurons this run may spend on llm_extract: it stops once the budget is reached, "
                "and the last call may pass it by its own cost (positive; required for that kind, no default)"
            ),
        ),
    ] = None,
    concurrency: Annotated[
        int,
        typer.Option(
            "--concurrency",
            min=1,
            max=MAX_LLM_CONCURRENCY,
            help=(
                f"Model calls in flight at once, 1 to {MAX_LLM_CONCURRENCY} (default 1); above 1 only with "
                "--kinds llm_extract, settled in waves of this size"
            ),
        ),
    ] = 1,
    kinds: Annotated[
        str,
        typer.Option(
            "--kinds",
            help=(
                "Comma separated task kinds to claim (default fetch_url,enrich_metadata,harvest_payload,extract_page; "
                "render_page and capture_screenshot need Cloudflare settings and artifact storage; llm_extract also "
                "needs the Workers AI token, LLM_MODEL, a readable ledger and --neuron-budget)"
            ),
        ),
    ] = ",".join(WORKER_DEFAULT_TASK_KINDS),
) -> None:
    """Claim tasks, fetch URLs, complete or fail."""
    if max_tasks == 0:
        fail("invalid drain bounds: max_tasks must be between 1 and 50", EXIT_USAGE)
    options = DrainOptions(
        kinds=task_kinds(kinds),
        max_tasks=max_tasks,
        max_batches=max_batches,
        time_budget_seconds=time_budget_seconds,
        browser_budget_seconds=browser_budget_seconds,
        neuron_budget=neuron_budget,
        concurrency=concurrency,
    )
    try:
        options.policy()
    except ValueError as err:
        fail(f"invalid drain bounds: {err}", EXIT_USAGE)
    settings = settings_of(ctx)
    try:
        report = run_drain(options, settings, api_client(ctx))
    except (BrowserSetupError, LlmSetupError) as err:
        fail(str(err), err.exit_code)
    except DiscoveryMachineApiError as err:
        fail(f"drain failed: {err}")
    typer.echo(json.dumps(report.model_dump(mode="json")))
    if not report.succeeded:
        raise typer.Exit(EXIT_FAILED)
