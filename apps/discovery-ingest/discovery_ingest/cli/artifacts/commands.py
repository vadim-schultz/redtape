"""``artifacts``: stored page snapshots and screenshots, brought to a developer as fixtures."""

from pathlib import Path
from typing import Annotated
from uuid import UUID

import typer

from discovery_ingest.artifacts import ArtifactKind, ArtifactRead
from discovery_ingest.cli.context import api_client
from discovery_ingest.cli.errors import HELP_OPTIONS, handles_api_errors, show_help_without_subcommand
from discovery_ingest.cli.options import positive_int
from discovery_ingest.operations.artifact_export import artifact_pages, write_artifact

artifacts_app = typer.Typer(
    name="artifacts",
    help="Stored page snapshots and screenshots",
    add_completion=False,
    pretty_exceptions_enable=False,
    rich_markup_mode=None,
    context_settings=HELP_OPTIONS,
)


@artifacts_app.callback(invoke_without_command=True)
def artifacts_group(ctx: typer.Context) -> None:
    """Work with stored page snapshots and screenshots."""
    show_help_without_subcommand(ctx)


def _tsv_line(artifact: ArtifactRead) -> str:
    """Return the four tab-separated columns the fixture-capture workflow reads: id, kind, size, source url."""
    return "\t".join([str(artifact.id), artifact.kind, str(artifact.byte_size), artifact.source_url])


@artifacts_app.command("list")
@handles_api_errors("artifacts")
def artifacts_list(
    ctx: typer.Context,
    host: Annotated[str, typer.Option("--host", help="Source host, for example verwaltung.bund.de")],
    limit: Annotated[
        int, typer.Option("--limit", parser=positive_int, help="Maximum artifacts to print (default 20)")
    ] = 20,
    kind: Annotated[ArtifactKind, typer.Option("--kind")] = "html_snapshot",
) -> None:
    """Print id, kind, size and source url of stored artifacts of a host."""
    for artifact in artifact_pages(api_client(ctx), host, kind, limit):
        typer.echo(_tsv_line(artifact))


@artifacts_app.command("download")
@handles_api_errors("artifacts")
def artifacts_download(
    ctx: typer.Context,
    artifact_id: Annotated[UUID, typer.Option("--id", help="Artifact id from `artifacts list`")],
    out: Annotated[Path, typer.Option("--out", help="File to write; parent directories are created")],
) -> None:
    """Write the stored bytes of one artifact to a file."""
    size = write_artifact(api_client(ctx), artifact_id, out)
    typer.echo(f"wrote {out} ({size} bytes)")
