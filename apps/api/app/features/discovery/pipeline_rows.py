"""Row-to-dict mappers and stage derivation for the admin pipeline read."""

from __future__ import annotations

from app.features.discovery.pipeline import derive_pipeline_stage, stage_input
from app.models.discovery import (
    DiscoveryClaim,
    DiscoveryFetchLog,
)


def stage_of(task_count: int, fetch_logs: list[DiscoveryFetchLog], claims: list[DiscoveryClaim]) -> str:
    """Derive the stage for the admin read without touching the stored row."""
    return derive_pipeline_stage(
        stage_input(
            task_count=task_count,
            has_fetch_log=len(fetch_logs) > 0,
            claims=[(c.kind, c.payload) for c in claims],
        )
    ).value
