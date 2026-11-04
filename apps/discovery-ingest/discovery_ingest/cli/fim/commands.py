"""``fim``: the FIM Portal enrich and the live steckbrief probe."""

from pathlib import Path
from typing import Annotated
from uuid import UUID

import typer

from discovery_ingest.cli.context import settings_of
from discovery_ingest.cli.enrich import catalogue_or_fail, post_enrichment
from discovery_ingest.cli.errors import (
    EXIT_FAILED,
    HELP_OPTIONS,
    handles_api_errors,
    show_help_without_subcommand,
)
from discovery_ingest.cli.options import steckbrief_keys
from discovery_ingest.config import DEFAULT_FIM_PORTAL_URL
from discovery_ingest.fim.client import FixtureSteckbriefSource
from discovery_ingest.operations.enrich import FimEnricher
from discovery_ingest.operations.probes import fim_probe

fim_app = typer.Typer(
    name="fim",
    help="FIM Portal enrich",
    add_completion=False,
    pretty_exceptions_enable=False,
    rich_markup_mode=None,
    context_settings=HELP_OPTIONS,
)


@fim_app.callback(invoke_without_command=True)
def fim_group(ctx: typer.Context) -> None:
    """FIM Portal enrich."""
    show_help_without_subcommand(ctx)


@fim_app.command("enrich")
@handles_api_errors("fim")
def fim_enrich(
    ctx: typer.Context,
    catalogue_service_id: Annotated[UUID, typer.Option("--catalogue-service-id")],
    catalogue_export: Annotated[str, typer.Option("--catalogue-export", help="Admin catalogue export JSON")],
    input_path: Annotated[str, typer.Option("--input", help="Steckbrief JSON fixture or snapshot")],
) -> None:
    """Upsert entity and claims from steckbrief."""
    settings = settings_of(ctx)
    catalogue = catalogue_or_fail(catalogue_export, catalogue_service_id)
    enricher = FimEnricher(FixtureSteckbriefSource.from_json_file(Path(input_path)), settings.fim_portal_base_url)
    post_enrichment(ctx, enricher, catalogue)


@fim_app.command("probe")
def fim_probe_command(
    keys: Annotated[str, typer.Option("--keys", help="Comma separated 14-digit keys")],
    base_url: Annotated[str, typer.Option("--base-url", help="FIM Portal base URL")] = DEFAULT_FIM_PORTAL_URL,
) -> None:
    """Report status and top-level keys of live steckbriefe."""
    outcome = fim_probe(base_url, steckbrief_keys(keys))
    typer.echo("\n".join(outcome.lines))
    if outcome.failed:
        raise typer.Exit(EXIT_FAILED)
