"""``embed``: Workers AI text embeddings: ``probe`` reports the model, ``drain`` embeds the queue, ``summary`` counts it."""

import json
from typing import Annotated

import typer

from discovery_ingest.cli.context import api_client, settings_of
from discovery_ingest.cli.errors import (
    EXIT_FAILED,
    EXIT_USAGE,
    HELP_OPTIONS,
    fail,
    handles_api_errors,
    show_help_without_subcommand,
)
from discovery_ingest.llm_settings import load_llm_settings
from discovery_ingest.operations.embed_drain import DEFAULT_NEURON_BUDGET, EmbedOptions, run_embed
from discovery_ingest.operations.embed_probe import embed_probe
from discovery_ingest.worker.llm_setup import LlmSetupError

EXIT_NOTHING_PENDING = 3

embed_app = typer.Typer(
    name="embed",
    help="Workers AI embeddings",
    add_completion=False,
    pretty_exceptions_enable=False,
    rich_markup_mode=None,
    context_settings=HELP_OPTIONS,
)


@embed_app.callback(invoke_without_command=True)
def embed_group(ctx: typer.Context) -> None:
    """Workers AI embeddings."""
    show_help_without_subcommand(ctx)


@embed_app.command("probe")
def embed_probe_command(
    model: Annotated[
        str | None, typer.Option("--model", help="A Workers AI embedding model id (default EMBEDDING_MODEL)")
    ] = None,
) -> None:
    """Probe the embedding model and print one JSON report."""
    settings = load_llm_settings()
    if settings.missing_ai_credentials():
        fail(f"missing environment: {', '.join(settings.missing_ai_credentials())}", EXIT_USAGE)
    outcome = embed_probe(settings, model=model or settings.embedding_model)
    typer.echo("\n".join(outcome.lines))
    if outcome.failed:
        raise typer.Exit(EXIT_FAILED)


@embed_app.command("drain")
def embed_drain(
    ctx: typer.Context,
    max_tasks: Annotated[
        int,
        typer.Option(
            "--max-tasks", help="Tasks per claim request, which is also the embedding batch (1-50, default 50)"
        ),
    ] = 50,
    max_batches: Annotated[
        int, typer.Option("--max-batches", help="Maximum claim/embed batches (positive, default 1)")
    ] = 1,
    time_budget_seconds: Annotated[
        float | None,
        typer.Option("--time-budget-seconds", help="Optional positive wall-clock budget for the whole drain"),
    ] = None,
    neuron_budget: Annotated[
        float,
        typer.Option(
            "--neuron-budget",
            help=(
                "Workers AI neurons this run may spend: it stops once the budget is reached, and the last call may "
                "pass it by its own cost (positive, default 3000)"
            ),
        ),
    ] = DEFAULT_NEURON_BUDGET,
) -> None:
    """Claim embedding tasks, embed them on Workers AI and post the vectors."""
    options = EmbedOptions(max_tasks, max_batches, time_budget_seconds, neuron_budget)
    try:
        options.policy()
    except ValueError as err:
        fail(f"invalid drain bounds: {err}", EXIT_USAGE)
    try:
        report = run_embed(options, settings_of(ctx), api_client(ctx))
    except LlmSetupError as err:
        fail(str(err), err.exit_code)
    typer.echo(json.dumps(report.model_dump(mode="json")))
    if not report.succeeded:
        raise typer.Exit(EXIT_FAILED)


@embed_app.command("summary")
@handles_api_errors("embed")
def embed_summary(
    ctx: typer.Context,
    require_pending: Annotated[
        bool,
        typer.Option("--require-pending", help="Exit 3 when no embedding task is ready (the workflow skips the drain)"),
    ] = False,
) -> None:
    """Print the embedding queue counts; exit 3 when ``--require-pending`` finds nothing ready."""
    summary = api_client(ctx).embeddings.summary(settings_of(ctx).embedding_model)
    typer.echo(json.dumps(summary.model_dump(mode="json")))
    if require_pending and summary.pending_ready == 0:
        typer.echo("nothing to embed: no embedding task is ready", err=True)
        raise typer.Exit(EXIT_NOTHING_PENDING)
