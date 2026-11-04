"""What the commands share: the ingest settings and the API client, each built on first use and closed on exit."""

from __future__ import annotations

import typer

from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.config import IngestSettings, load_ingest_settings


class CliContext:
    """The lazy ``ctx.obj``: nothing is read from the environment until a command asks for it.

    ``--help`` and the probes never touch it, so they run without ``DISCOVERY_API_URL`` and ``DISCOVERY_API_KEY``.
    """

    def __init__(self) -> None:
        """Start with nothing loaded and nothing open."""
        self._settings: IngestSettings | None = None
        self._client: DiscoveryIngestClient | None = None

    def settings(self) -> IngestSettings:
        """Return the ingest settings, reading the environment on the first call."""
        if self._settings is None:
            self._settings = load_ingest_settings()
        return self._settings

    def client(self) -> DiscoveryIngestClient:
        """Return the API client, building it from the settings on the first call."""
        if self._client is None:
            self._client = DiscoveryIngestClient.from_settings(self.settings())
        return self._client

    def close(self) -> None:
        """Close the API client if one was built; called when the root command finishes."""
        if self._client is not None:
            self._client.close()


def context_of(ctx: typer.Context) -> CliContext:
    """Return the shared context the root callback put in ``ctx.obj``."""
    return ctx.ensure_object(CliContext)


def settings_of(ctx: typer.Context) -> IngestSettings:
    """Return the ingest settings for this invocation."""
    return context_of(ctx).settings()


def api_client(ctx: typer.Context) -> DiscoveryIngestClient:
    """Return the API client for this invocation."""
    return context_of(ctx).client()
