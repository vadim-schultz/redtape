"""``translate probe``: cost an engine on a fixed sample of real candidates and write a spot-check sheet."""

from pathlib import Path
from typing import Annotated

import typer

from discovery_ingest.cli.errors import EXIT_FAILED, EXIT_USAGE, fail
from discovery_ingest.cli.translate.app import translate_app
from discovery_ingest.operations.translate_probe import TranslateProbeRequest, translate_probe
from discovery_ingest.translation.locale_codes import UnmappedLocaleError, require_coverage
from discovery_ingest.translation.registry import UnknownEngineError, require_registered
from discovery_ingest.translation.settings import ProbeSourceSettings, load_translation_settings

DEFAULT_SAMPLE = 50
DEFAULT_MAX_USAGE = 3000.0
DEFAULT_DAILY_BUDGET = 9500.0


def _engine_for(engine: str | None, locale: str) -> str:
    """Return the engine to probe (the option, else ``TRANSLATION_ENGINE``) once it and its locale map check out, or exit 2."""
    chosen = engine or load_translation_settings().translation_engine
    try:
        require_registered(chosen)
        require_coverage(chosen, [locale])
    except (UnknownEngineError, UnmappedLocaleError) as err:
        fail(str(err), EXIT_USAGE)
    return chosen


def _positive(name: str, value: float) -> None:
    if value < 1:
        fail(f"{name} must be at least 1", EXIT_USAGE)


@translate_app.command("probe")
def translate_probe_command(
    locale: Annotated[str, typer.Option("--locale", help="Target locale code, for example tr")],
    sample: Annotated[int, typer.Option("--sample", help="Real candidates to translate")] = DEFAULT_SAMPLE,
    engine: Annotated[
        str | None, typer.Option("--engine", help="A registered engine (default TRANSLATION_ENGINE)")
    ] = None,
    model: Annotated[str | None, typer.Option("--model", help="Model override for the engine")] = None,
    sheet: Annotated[
        Path | None,
        typer.Option("--sheet", help="Spot-check sheet (CSV); default translation-probe/<engine>-<locale>.csv"),
    ] = None,
    max_usage: Annotated[
        float, typer.Option("--max-usage", help="Stop after this much usage (neurons or characters)")
    ] = DEFAULT_MAX_USAGE,
    daily_budget: Annotated[
        float, typer.Option("--daily-budget", help="Neurons a day for translation, for the days projection")
    ] = DEFAULT_DAILY_BUDGET,
) -> None:
    """Translate a fixed sample of the public candidates and print one JSON report (nothing is stored)."""
    for name, value in (("--sample", sample), ("--max-usage", max_usage), ("--daily-budget", daily_budget)):
        _positive(name, value)
    request = TranslateProbeRequest(_engine_for(engine, locale), locale, sample, model, sheet, max_usage, daily_budget)
    source = ProbeSourceSettings()
    if source.missing():
        fail(f"missing environment: {', '.join(source.missing())}", EXIT_USAGE)
    try:
        outcome = translate_probe(request, source.discovery_api_url or "")
    except ValueError as err:
        fail(str(err), EXIT_USAGE)
    typer.echo("\n".join(outcome.lines))
    if outcome.failed:
        raise typer.Exit(EXIT_FAILED)
