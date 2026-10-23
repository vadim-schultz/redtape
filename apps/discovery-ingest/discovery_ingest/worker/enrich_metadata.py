"""Handle enrich_metadata discovery tasks (FIM steckbrief to entities/claims)."""

from __future__ import annotations

import json
from typing import Any

from discovery_ingest.api_client import DiscoveryMachineApiError, DiscoveryMachineClient
from discovery_ingest.enrich import (
    catalogue_export_item_from_machine,
    fim_steckbrief_claim_requests,
    fim_steckbrief_entity_request,
)
from discovery_ingest.schemas import ClaimedTask
from discovery_ingest.worker.fetcher import PoliteUrlFetcher
from discovery_ingest.worker.settle import fail_from_outcome, fail_permanently

_DEFAULT_FIM_BASE = "https://fimportal.de"


def handle_enrich_metadata(
    task: ClaimedTask,
    *,
    client: DiscoveryMachineClient,
    fetcher: PoliteUrlFetcher,
    fim_base_url: str = _DEFAULT_FIM_BASE,
) -> str:
    """Fetch steckbrief JSON and upsert entity and claims via the machine API."""
    try:
        catalogue = client.get_catalogue(task.catalogue_service_id)
    except DiscoveryMachineApiError as err:
        return fail_permanently(client, task.id, err.detail)

    outcome = fetcher.get(task.target_url)
    if outcome.failed:
        return fail_from_outcome(client, task.id, outcome)

    steckbrief = _parse_steckbrief_body(outcome.body)
    if steckbrief is None:
        return fail_permanently(client, task.id, "steckbrief response is not JSON object")

    export_row = catalogue_export_item_from_machine(catalogue)
    try:
        entity_body = fim_steckbrief_entity_request(export_row, steckbrief, fim_base_url=fim_base_url)
    except ValueError as err:
        return fail_permanently(client, task.id, str(err))

    try:
        entity = client.post_entity(entity_body)
        for claim in fim_steckbrief_claim_requests(
            export_row,
            steckbrief,
            entity_id=entity.id,
            fim_base_url=fim_base_url,
        ):
            client.post_claim(claim)
    except DiscoveryMachineApiError as err:
        return fail_permanently(client, task.id, err.detail)

    client.complete_task(task.id)
    return "completed"


def _parse_steckbrief_body(body: bytes | None) -> dict[str, Any] | None:
    if body is None:
        return None
    try:
        parsed = json.loads(body.decode())
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed
