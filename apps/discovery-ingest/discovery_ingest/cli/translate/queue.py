"""``translate drain`` and ``translate summary``: drain the translation queue, count it."""

from __future__ import annotations

import json
from typing import Annotated

import typer
from pydantic import ValidationError

from discovery_ingest.cli.context import api_client
from discovery_ingest.cli.errors import EXIT_FAILED, EXIT_USAGE, fail, handles_api_errors
from discovery_ingest.cli.translate.app import translate_app
from discovery_ingest.operations.translate_drain import (
    DEFAULT_CONCURRENCY,
    DEFAULT_NEURON_BUDGET,
    DEFAULT_TASKS_PER_BATCH,
    TranslateOptions,
    run_translate,
)
from discovery_ingest.translation.meter import NoMeterForUnitError
from discovery_ingest.translation.settings import TranslationSettings, load_translation_settings
from discovery_ingest.worker.llm_setup import LlmSetupError

EXIT_NOTHING_PENDING = 3


def _settings() -> TranslationSettings:
    try:
        return load_translation_settings()
    except ValidationError as err:
        fail(f"invalid translation settings: {err}", EXIT_USAGE)


def _options_or_exit(options: TranslateOptions) -> None:
    try:
        options.policy()
    except ValueError as err:
        fail(f"invalid drain bounds: {err}", EXIT_USAGE)


@translate_app.command("drain")
def translate_drain(
    ctx: typer.Context,
    max_tasks: Annotated[
        int,
        typer.Option(
            "--max-tasks", help="Tasks per claim request, grouped by locale into one prompt each (1-50, default 10)"
        ),
    ] = DEFAULT_TASKS_PER_BATCH,
    max_batches: Annotated[
        int, typer.Option("--max-batches", help="Maximum claim/translate batches (positive, default 1)")
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
                "Neurons this run may spend when the engine is billed in neurons: it stops once the budget is "
                "reached, and never takes the day's ledger below QUERY_EMBED_RESERVE (positive, default 2500)"
            ),
        ),
    ] = DEFAULT_NEURON_BUDGET,
    concurrency: Annotated[
        int,
        typer.Option(
            "--concurrency",
            help="Engine calls in flight at once, capped by the engine (claude-code 1-4, default 2; llm 1)",
        ),
    ] = DEFAULT_CONCURRENCY,
) -> None:
    """Claim translation tasks, translate them with TRANSLATION_ENGINE and post the text."""
    options = TranslateOptions(max_tasks, max_batches, time_budget_seconds, neuron_budget, concurrency)
    _options_or_exit(options)
    try:
        report = run_translate(options, _settings(), api_client(ctx))
    except LlmSetupError as err:
        fail(str(err), err.exit_code)
    except NoMeterForUnitError as err:
        fail(str(err), EXIT_USAGE)
    typer.echo(json.dumps(report.model_dump(mode="json")))
    if not report.succeeded:
        raise typer.Exit(EXIT_FAILED)


@translate_app.command("summary")
@handles_api_errors("translate")
def translate_summary(
    ctx: typer.Context,
    require_pending: Annotated[
        bool,
        typer.Option(
            "--require-pending", help="Exit 3 when no translation task is ready (the workflow skips the drain)"
        ),
    ] = False,
) -> None:
    """Print the translation queue counts per locale; exit 3 when ``--require-pending`` finds nothing ready."""
    summary = api_client(ctx).translations.summary()
    typer.echo(json.dumps({**summary.model_dump(mode="json"), "pending_ready": summary.pending_ready}))
    if require_pending and summary.pending_ready == 0:
        typer.echo("nothing to translate: no translation task is ready", err=True)
        raise typer.Exit(EXIT_NOTHING_PENDING)
