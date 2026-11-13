"""``translate probe``: cost an engine on a fixed sample of real candidates, or measure azure-translator on the reviewed units."""

from pathlib import Path
from typing import Annotated

import typer

from discovery_ingest.cli.errors import EXIT_FAILED, EXIT_USAGE, fail
from discovery_ingest.cli.translate.app import translate_app
from discovery_ingest.operations.probes import ProbeOutcome
from discovery_ingest.operations.translate_probe import (
    AzureProbeRequest,
    TranslateProbeRequest,
    translate_azure_probe,
    translate_probe,
)
from discovery_ingest.translation.locale_codes import DEFAULT_TARGET_LOCALES, UnmappedLocaleError, require_coverage
from discovery_ingest.translation.probe_azure_units import FIXTURE_PATH
from discovery_ingest.translation.registry import UnknownEngineError, require_registered
from discovery_ingest.translation.settings import ProbeSourceSettings, load_translation_settings

AZURE_ENGINE = "azure-translator"
DEFAULT_SAMPLE = 50
DEFAULT_MAX_USAGE = 3000.0
DEFAULT_AZURE_MAX_CHARACTERS = 10_000.0
DEFAULT_DAILY_BUDGET = 9500.0


def _engine_for(engine: str | None) -> str:
    """Return the engine to probe (the option, else ``TRANSLATION_ENGINE``) once it is registered, or exit 2."""
    chosen = engine or load_translation_settings().translation_engine
    try:
        require_registered(chosen)
    except UnknownEngineError as err:
        fail(str(err), EXIT_USAGE)
    return chosen


def _locales(engine: str, locale: str | None) -> tuple[str, ...]:
    """Return the locales to probe: the one given, or every target locale for azure-translator; exit 2 otherwise."""
    if locale is None and engine != AZURE_ENGINE:
        fail("--locale is required for every engine but azure-translator", EXIT_USAGE)
    locales = (locale,) if locale is not None else DEFAULT_TARGET_LOCALES
    try:
        require_coverage(engine, locales)
    except UnmappedLocaleError as err:
        fail(str(err), EXIT_USAGE)
    return locales


def _positive(name: str, value: float) -> None:
    if value < 1:
        fail(f"{name} must be at least 1", EXIT_USAGE)


def _max_usage(engine: str, given: float | None) -> float:
    """Return the spend cap: the option, else 10,000 characters for azure-translator and 3,000 usage for the others."""
    if given is not None:
        return given
    return DEFAULT_AZURE_MAX_CHARACTERS if engine == AZURE_ENGINE else DEFAULT_MAX_USAGE


def _candidate_probe(request: TranslateProbeRequest) -> ProbeOutcome:
    """Probe a sample of the public candidates; the list is read first, and nothing is stored."""
    source = ProbeSourceSettings()
    if source.missing():
        fail(f"missing environment: {', '.join(source.missing())}", EXIT_USAGE)
    try:
        return translate_probe(request, source.discovery_api_url or "")
    except ValueError as err:
        fail(str(err), EXIT_USAGE)


def _azure_probe(request: AzureProbeRequest) -> ProbeOutcome:
    """Probe azure-translator on the reviewed units; a missing fixture or credential exits 2 before any request."""
    try:
        return translate_azure_probe(request)
    except ValueError as err:
        fail(str(err), EXIT_USAGE)


@translate_app.command("probe")
def translate_probe_command(
    locale: Annotated[
        str | None,
        typer.Option(
            "--locale", help="Target locale code, for example tr (azure-translator: every target locale when unset)"
        ),
    ] = None,
    sample: Annotated[
        int, typer.Option("--sample", help="Real candidates to translate (not azure-translator)")
    ] = DEFAULT_SAMPLE,
    engine: Annotated[
        str | None, typer.Option("--engine", help="A registered engine (default TRANSLATION_ENGINE)")
    ] = None,
    model: Annotated[str | None, typer.Option("--model", help="Model override for the engine")] = None,
    sheet: Annotated[
        Path | None,
        typer.Option(
            "--sheet",
            help="Spot-check sheet (CSV), not azure-translator; default translation-probe/<engine>-<locale>.csv",
        ),
    ] = None,
    max_usage: Annotated[
        float | None,
        typer.Option(
            "--max-usage",
            help="Stop after this much usage (neurons, characters or tokens; default 3000, or 10000 characters for azure-translator)",
        ),
    ] = None,
    daily_budget: Annotated[
        float,
        typer.Option(
            "--daily-budget", help="Neurons a day for translation, for the days projection (not azure-translator)"
        ),
    ] = DEFAULT_DAILY_BUDGET,
    units: Annotated[
        Path | None,
        typer.Option(
            "--units", help="azure-translator: the reviewed units, JSON; default tests/fixtures/azure_probe_units.json"
        ),
    ] = None,
    report: Annotated[
        Path | None, typer.Option("--report", help="azure-translator: also write the JSON report to this file")
    ] = None,
) -> None:
    """Probe an engine and print one JSON report (nothing is stored): a candidate sample, or azure-translator on the reviewed units."""
    for name, value in (("--sample", sample), ("--daily-budget", daily_budget)):
        _positive(name, value)
    if max_usage is not None:
        _positive("--max-usage", max_usage)
    chosen = _engine_for(engine)
    locales = _locales(chosen, locale)
    if chosen == AZURE_ENGINE:
        outcome = _azure_probe(AzureProbeRequest(locales, units or FIXTURE_PATH, _max_usage(chosen, max_usage), report))
    else:
        if units is not None or report is not None:
            fail("--units and --report are for azure-translator", EXIT_USAGE)
        request = TranslateProbeRequest(
            chosen, locales[0], sample, model, sheet, _max_usage(chosen, max_usage), daily_budget
        )
        outcome = _candidate_probe(request)
    typer.echo("\n".join(outcome.lines))
    if outcome.failed:
        raise typer.Exit(EXIT_FAILED)
