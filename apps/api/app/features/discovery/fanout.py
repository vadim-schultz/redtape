"""Policy rules that enqueue secondary discovery tasks after catalogue upsert."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.features.discovery.repository import DiscoveryRepository
from app.models.discovery import (
    CatalogueService,
    DiscoveryEventType,
    DiscoverySource,
    DiscoveryTask,
    DiscoveryTaskKind,
)

FIM_PORTAL_BASE_URL = "https://fimportal.de"
ENRICH_METADATA_PRIORITY = 200


@dataclass(frozen=True, slots=True)
class FanoutTaskSpec:
    """One task to enqueue when fanout policy matches a catalogue row."""

    kind: DiscoveryTaskKind
    target_url: str
    priority: int


def _fim_id_from_payload(raw_payload: dict) -> str | None:
    value = raw_payload.get("fim_id")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _fim_enrich_spec(service: CatalogueService) -> FanoutTaskSpec | None:
    if service.source != DiscoverySource.GOVDATA:
        return None
    fim_id = _fim_id_from_payload(service.raw_payload)
    if fim_id is None:
        return None
    target_url = f"{FIM_PORTAL_BASE_URL}/api/v1/leistung-steckbriefe/{fim_id}"
    return FanoutTaskSpec(
        kind=DiscoveryTaskKind.ENRICH_METADATA,
        target_url=target_url,
        priority=ENRICH_METADATA_PRIORITY,
    )


FanoutRule = Callable[[CatalogueService], FanoutTaskSpec | None]

FANOUT_RULES: tuple[FanoutRule, ...] = (_fim_enrich_spec,)


def fanout_specs_for_service(service: CatalogueService) -> list[FanoutTaskSpec]:
    """Return task specs implied by fanout policy for ``service``."""
    specs: list[FanoutTaskSpec] = []
    for rule in FANOUT_RULES:
        spec = rule(service)
        if spec is not None:
            specs.append(spec)
    return specs


def apply_fanout_for_service(repo: DiscoveryRepository, service: CatalogueService) -> list[DiscoveryTask]:
    """Insert pending fanout tasks and record ``task_enqueued`` events (idempotent)."""
    created: list[DiscoveryTask] = []
    for spec in fanout_specs_for_service(service):
        existing = repo.find_pending_task(
            catalogue_service_id=service.id,
            kind=spec.kind,
            target_url=spec.target_url,
        )
        if existing is not None:
            continue
        task = repo.insert_task(
            catalogue_service_id=service.id,
            kind=spec.kind,
            target_url=spec.target_url,
            priority=spec.priority,
        )
        repo.record_event(
            event_type=DiscoveryEventType.TASK_ENQUEUED,
            catalogue_service_id=service.id,
            discovery_task_id=task.id,
            payload={"kind": task.kind.value, "target_url": task.target_url},
        )
        created.append(task)
    return created
