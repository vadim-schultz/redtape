"""Policy rules that enqueue secondary discovery tasks after catalogue upsert."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.features.discovery.repository import DiscoveryRepository, TaskTarget
from app.features.discovery.steckbrief_key import steckbrief_key
from app.features.discovery.task_enqueue import enqueue_task_with_outcome
from app.models.discovery import (
    CatalogueService,
    DiscoverySource,
    DiscoveryTask,
    DiscoveryTaskKind,
)

FIM_PORTAL_BASE_URL = "https://fimportal.de"
ENRICH_METADATA_PRIORITY = 200
HARVEST_PAYLOAD_PRIORITY = 50
FIM_ENRICH_SOURCES = frozenset({DiscoverySource.GOVDATA, DiscoverySource.PVOG})
# Keep equal to EXTRACTOR_VERSION in apps/discovery-ingest/discovery_ingest/harvest/pvog.py; a bump re-harvests.
PVOG_HARVESTER_VERSION = "1"


@dataclass(frozen=True, slots=True)
class FanoutTaskSpec:
    """One task to enqueue when fanout policy matches a catalogue row."""

    kind: DiscoveryTaskKind
    target_url: str
    priority: int
    input_key: str | None = None


def _fim_enrich_spec(service: CatalogueService) -> FanoutTaskSpec | None:
    if service.source not in FIM_ENRICH_SOURCES:
        return None
    key = steckbrief_key(service.raw_payload)
    if key is None:
        return None
    return FanoutTaskSpec(
        kind=DiscoveryTaskKind.ENRICH_METADATA,
        target_url=f"{FIM_PORTAL_BASE_URL}/api/v1/leistung-steckbriefe/{key}",
        priority=ENRICH_METADATA_PRIORITY,
    )


def _has_details(raw_payload: dict) -> bool:
    details = raw_payload.get("details")
    return isinstance(details, list) and len(details) > 0


def _harvest_spec(service: CatalogueService) -> FanoutTaskSpec | None:
    if service.source != DiscoverySource.PVOG or not _has_details(service.raw_payload):
        return None
    return FanoutTaskSpec(
        kind=DiscoveryTaskKind.HARVEST_PAYLOAD,
        target_url=service.portal_url or f"pvog-payload:{service.external_id}",
        priority=HARVEST_PAYLOAD_PRIORITY,
        input_key=f"pvog-payload@{PVOG_HARVESTER_VERSION}",
    )


FanoutRule = Callable[[CatalogueService], FanoutTaskSpec | None]

FANOUT_RULES: tuple[FanoutRule, ...] = (_fim_enrich_spec, _harvest_spec)


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
    outcomes = [
        enqueue_task_with_outcome(repo, _target(service, spec), priority=spec.priority)
        for spec in fanout_specs_for_service(service)
    ]
    return [outcome.task for outcome in outcomes if outcome.created]


def _target(service: CatalogueService, spec: FanoutTaskSpec) -> TaskTarget:
    return TaskTarget(
        catalogue_service_id=service.id, kind=spec.kind, target_url=spec.target_url, input_key=spec.input_key
    )
