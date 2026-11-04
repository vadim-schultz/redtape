"""``leika``: the LeiKa stammtext enrich."""

from pathlib import Path
from typing import Annotated
from uuid import UUID

import typer

from discovery_ingest.cli.context import settings_of
from discovery_ingest.cli.enrich import catalogue_or_fail, post_enrichment
from discovery_ingest.cli.errors import HELP_OPTIONS, handles_api_errors, show_help_without_subcommand
from discovery_ingest.leika.client import FixtureStammtextSource
from discovery_ingest.operations.enrich import LeikaEnricher

leika_app = typer.Typer(
    name="leika",
    help="LeiKa stammtext enrich",
    add_completion=False,
    pretty_exceptions_enable=False,
    rich_markup_mode=None,
    context_settings=HELP_OPTIONS,
)


@leika_app.callback(invoke_without_command=True)
def leika_group(ctx: typer.Context) -> None:
    """LeiKa stammtext enrich."""
    show_help_without_subcommand(ctx)


@leika_app.command("enrich")
@handles_api_errors("leika")
def leika_enrich(
    ctx: typer.Context,
    catalogue_service_id: Annotated[UUID, typer.Option("--catalogue-service-id")],
    catalogue_export: Annotated[str, typer.Option("--catalogue-export", help="Admin catalogue export JSON")],
    input_path: Annotated[str, typer.Option("--input", help="Stammtext JSON fixture or snapshot")],
) -> None:
    """Upsert entity and claims from LeiKa stammtext."""
    settings = settings_of(ctx)
    catalogue = catalogue_or_fail(catalogue_export, catalogue_service_id)
    enricher = LeikaEnricher(FixtureStammtextSource.from_json_file(Path(input_path)), settings.fim_portal_base_url)
    post_enrichment(ctx, enricher, catalogue)
