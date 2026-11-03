"""Row-to-dict mappers and stage derivation for the admin pipeline read."""

from __future__ import annotations

from app.features.discovery.pipeline import derive_pipeline_stage, stage_input
from app.models.discovery import (
    DiscoveryClaim,
    DiscoveryEntity,
    DiscoveryEvent,
    DiscoveryFetchLog,
)


def fetch_log_dict(row: DiscoveryFetchLog) -> dict[str, object]:
    """Map a fetch log row to its admin JSON shape."""
    return {
        "id": str(row.id),
        "discovery_task_id": str(row.discovery_task_id),
        "http_status": row.http_status,
        "fetched_at": row.fetched_at.isoformat(),
        "content_type": row.content_type,
        "byte_length": row.byte_length,
        "error_message": row.error_message,
    }


def entity_dict(row: DiscoveryEntity) -> dict[str, object]:
    """Map an entity row to its admin JSON shape."""
    return {
        "id": str(row.id),
        "catalogue_service_id": str(row.catalogue_service_id),
        "canonical_url": row.canonical_url,
        "label": row.label,
        "created_at": row.created_at.isoformat(),
    }


def claim_dict(row: DiscoveryClaim) -> dict[str, object]:
    """Map a claim row to its admin JSON shape."""
    return {
        "id": str(row.id),
        "discovery_entity_id": str(row.discovery_entity_id),
        "kind": row.kind.value,
        "payload": row.payload,
        "confidence": float(row.confidence) if row.confidence is not None else None,
        "created_at": row.created_at.isoformat(),
    }


def event_dict(row: DiscoveryEvent) -> dict[str, object]:
    """Map an event row to its admin JSON shape."""
    return {
        "id": str(row.id),
        "event_type": row.event_type.value,
        "catalogue_service_id": str(row.catalogue_service_id) if row.catalogue_service_id else None,
        "discovery_task_id": str(row.discovery_task_id) if row.discovery_task_id else None,
        "payload": row.payload,
        "created_at": row.created_at.isoformat(),
    }


def stage_of(task_count: int, fetch_logs: list[DiscoveryFetchLog], claims: list[DiscoveryClaim]) -> str:
    """Derive the stage for the admin read without touching the stored row."""
    return derive_pipeline_stage(
        stage_input(
            task_count=task_count,
            has_fetch_log=len(fetch_logs) > 0,
            claims=[(c.kind, c.payload) for c in claims],
        )
    ).value
