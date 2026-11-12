"""``translate drain`` and ``translate summary``: drain the translation queue of one unit, count it.

``--unit card`` (the default) drains the card queue with TRANSLATION_ENGINE. ``--unit snapshot`` drains the procedure-page
queue on azure-translator, up to five pages a claim, under the document share of the monthly character ledger.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Annotated, Literal

import typer
from pydantic import ValidationError

from discovery_ingest.cli.context import api_client
from discovery_ingest.cli.errors import EXIT_FAILED, EXIT_USAGE, fail, handles_api_errors
from discovery_ingest.cli.translate.app import translate_app
from discovery_ingest.operations.snapshot_drain import SnapshotOptions, document_budget_share, run_snapshot
from discovery_ingest.operations.translate_drain import (
    DEFAULT_CONCURRENCY,
    DEFAULT_NEURON_BUDGET,
    DEFAULT_TASKS_PER_BATCH,
    TranslateOptions,
    run_translate,
)
from discovery_ingest.schemas import DrainReport
from discovery_ingest.translation.meter import NoMeterForUnitError
from discovery_ingest.translation.settings import TranslationSettings, load_translation_settings
from discovery_ingest.worker.llm_setup import LlmSetupError

EXIT_NOTHING_PENDING = 3
Unit = Literal["card", "snapshot"]
UnitOption = Annotated[
    Unit, typer.Option("--unit", help="card (default): the card queue; snapshot: the procedure-page queue")
]
_NOTHING_READY = {
    "card": "nothing to translate: no translation task is ready",
    "snapshot": "nothing to translate: no snapshot task is ready",
}


def _settings() -> TranslationSettings:
    try:
        return load_translation_settings()
    except ValidationError as err:
        fail(f"invalid translation settings: {err}", EXIT_USAGE)


def _checked(policy: Callable[[], object]) -> None:
    try:
        policy()
    except ValueError as err:
        fail(f"invalid drain bounds: {err}", EXIT_USAGE)


def _card_report(ctx: typer.Context, options: TranslateOptions) -> DrainReport:
    _checked(options.policy)
    return run_translate(options, _settings(), api_client(ctx))


def _snapshot_report(ctx: typer.Context, options: SnapshotOptions) -> DrainReport:
    _checked(options.policy)
    _checked(document_budget_share)
    return run_snapshot(options, api_client(ctx))


@translate_app.command("drain")
def translate_drain(
    ctx: typer.Context,
    unit: UnitOption = "card",
    max_tasks: Annotated[
        int,
        typer.Option(
            "--max-tasks",
            help=(
                "Tasks per claim request, grouped by locale into one prompt each (1-50, default 10). "
                "With --unit snapshot the claim is at most 5 pages: pass --max-tasks 5"
            ),
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
    """Claim translation tasks of one unit and translate them: cards with TRANSLATION_ENGINE, pages on azure-translator."""
    try:
        if unit == "snapshot":
            report = _snapshot_report(ctx, SnapshotOptions(max_tasks, max_batches, time_budget_seconds))
        else:
            card = TranslateOptions(max_tasks, max_batches, time_budget_seconds, neuron_budget, concurrency)
            report = _card_report(ctx, card)
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
    unit: UnitOption = "card",
    require_pending: Annotated[
        bool,
        typer.Option(
            "--require-pending",
            help="Exit 3 when no translation task is ready (the workflow skips the drain); snapshot counts pages",
        ),
    ] = False,
) -> None:
    """Print the queue counts per locale for one unit; exit 3 when ``--require-pending`` finds nothing ready."""
    client = api_client(ctx)
    summary = client.snapshots.summary() if unit == "snapshot" else client.translations.summary()
    typer.echo(json.dumps({**summary.model_dump(mode="json"), "pending_ready": summary.pending_ready}))
    if require_pending and summary.pending_ready == 0:
        typer.echo(_NOTHING_READY[unit], err=True)
        raise typer.Exit(EXIT_NOTHING_PENDING)
