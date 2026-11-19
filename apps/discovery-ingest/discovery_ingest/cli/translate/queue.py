"""``translate drain`` and ``translate summary``: drain the translation queue of one unit, count it.

``--unit card`` (the default) drains the card queue with TRANSLATION_ENGINE, or with ``--engine``, and may bound the
claim to a priority band. ``--unit snapshot`` drains the procedure-page queue on azure-translator, up to five pages a
claim, under the document share of the monthly character ledger; it takes neither ``--engine`` nor a band.
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
from discovery_ingest.translation.registry import UnknownEngineError, require_registered
from discovery_ingest.translation.settings import TranslationSettings, load_translation_settings
from discovery_ingest.translation_models import PriorityBand
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


def _engine_option(engine: str | None) -> str | None:
    """Return ``engine`` once it is registered (``None`` keeps TRANSLATION_ENGINE); exit 2 when it is not."""
    if engine is None:
        return None
    try:
        return require_registered(engine)
    except UnknownEngineError as err:
        fail(str(err), EXIT_USAGE)


def _band_option(minimum: int | None, maximum: int | None) -> PriorityBand:
    """Return the priority band the flags name; exit 2 when a bound is negative or the band is inverted."""
    try:
        return PriorityBand(minimum=minimum, maximum=maximum)
    except ValidationError as err:
        fail(f"invalid priority band: {err}", EXIT_USAGE)


def _refuse_card_flags(engine: str | None, minimum: int | None, maximum: int | None) -> None:
    """Exit 2 when ``--unit snapshot`` is given an engine or a priority bound, which only the card drain takes."""
    if engine is not None or minimum is not None or maximum is not None:
        fail("--engine and --priority-min/--priority-max apply to --unit card only", EXIT_USAGE)


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
    engine: Annotated[
        str | None,
        typer.Option(
            "--engine",
            help=(
                "Card unit only: the engine that translates and claims these cards (default TRANSLATION_ENGINE). "
                "llm claims only the tail locales from its priority band up"
            ),
        ),
    ] = None,
    priority_min: Annotated[
        int | None,
        typer.Option("--priority-min", help="Card unit only: lowest claim priority this drain takes (0-1000 first)"),
    ] = None,
    priority_max: Annotated[
        int | None,
        typer.Option("--priority-max", help="Card unit only: highest claim priority this drain takes, inclusive"),
    ] = None,
) -> None:
    """Claim translation tasks of one unit and translate them: cards with TRANSLATION_ENGINE, pages on azure-translator."""
    try:
        if unit == "snapshot":
            _refuse_card_flags(engine, priority_min, priority_max)
            report = _snapshot_report(ctx, SnapshotOptions(max_tasks, max_batches, time_budget_seconds))
        else:
            card = TranslateOptions(
                max_tasks=max_tasks,
                max_batches=max_batches,
                time_budget_seconds=time_budget_seconds,
                neuron_budget=neuron_budget,
                concurrency=concurrency,
                engine=_engine_option(engine),
                band=_band_option(priority_min, priority_max),
            )
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
