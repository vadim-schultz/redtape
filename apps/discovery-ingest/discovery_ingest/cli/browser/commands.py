"""``browser``: Cloudflare Browser Run, probed with the two Cloudflare variables only."""

from typing import Annotated

import typer

from discovery_ingest.cli.errors import EXIT_FAILED, HELP_OPTIONS, fail, show_help_without_subcommand
from discovery_ingest.cli.options import probe_variant
from discovery_ingest.config import load_browser_settings
from discovery_ingest.operations.probes import browser_probe, canary_probe

DEFAULT_MAX_BROWSER_SECONDS = 240.0
EXIT_MISSING_SETTINGS = 2

browser_app = typer.Typer(
    name="browser",
    help="Cloudflare Browser Run",
    add_completion=False,
    pretty_exceptions_enable=False,
    rich_markup_mode=None,
    context_settings=HELP_OPTIONS,
)


@browser_app.callback(invoke_without_command=True)
def browser_group(ctx: typer.Context) -> None:
    """Cloudflare Browser Run."""
    show_help_without_subcommand(ctx)


@browser_app.command("probe")
def browser_probe_command(
    url: Annotated[
        list[str] | None, typer.Option("--url", help="A page to render with every variant (repeatable)")
    ] = None,
    error_url: Annotated[
        list[str] | None, typer.Option("--error-url", help="A page expected to fail; contract call only")
    ] = None,
    variant: Annotated[
        list[str] | None,
        typer.Option("--variant", parser=probe_variant, help="Only these variants (default all)"),
    ] = None,
    max_browser_seconds: Annotated[
        float,
        typer.Option(
            "--max-browser-seconds",
            help=f"Stop once this many browser seconds are spent (default {DEFAULT_MAX_BROWSER_SECONDS:g})",
        ),
    ] = DEFAULT_MAX_BROWSER_SECONDS,
    canary: Annotated[
        int | None,
        typer.Option(
            "--canary",
            min=1,
            help="Compare /content with the fused /snapshot on this many stable pages (from --url) and print the verdict",
        ),
    ] = None,
) -> None:
    """Call every quick action the worker uses and print a table; ``--canary`` runs the fused-render comparison instead."""
    settings = load_browser_settings()
    if settings.missing_credentials():
        fail(f"missing environment: {', '.join(settings.missing_credentials())}", EXIT_MISSING_SETTINGS)
    if canary is not None:
        outcome = canary_probe(settings, urls=url or [], required=canary, max_browser_seconds=max_browser_seconds)
    else:
        outcome = browser_probe(
            settings,
            urls=url or [],
            error_urls=error_url or [],
            variants=variant,
            max_browser_seconds=max_browser_seconds,
        )
    typer.echo("\n".join(outcome.lines))
    if outcome.failed:
        raise typer.Exit(EXIT_FAILED)
