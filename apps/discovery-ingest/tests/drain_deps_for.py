"""Build the :class:`DrainDeps` that the drain tests hand to ``run_worker_drain`` and ``run_recorded_drain``."""

from __future__ import annotations

from typing import Any

from discovery_ingest.worker.drain_deps import DrainDeps


def deps_for(client: Any, fetcher: Any, **overrides: Any) -> DrainDeps:
    """Return the deps for ``client`` and ``fetcher``; the keyword overrides are the optional collaborators."""
    return DrainDeps(client=client, fetcher=fetcher, **overrides)
