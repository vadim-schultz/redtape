"""``embed``: Workers AI text embeddings: ``probe`` reports the model's dimension, batch limit and cost."""

from typing import Annotated

import typer

from discovery_ingest.cli.errors import EXIT_FAILED, EXIT_USAGE, HELP_OPTIONS, fail, show_help_without_subcommand
from discovery_ingest.llm_settings import load_llm_settings
from discovery_ingest.operations.embed_probe import embed_probe

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
