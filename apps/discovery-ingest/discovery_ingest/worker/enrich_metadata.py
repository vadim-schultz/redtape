"""Handle enrich_metadata discovery tasks (FIM steckbrief to entities/claims)."""

from __future__ import annotations

from discovery_ingest.client import DiscoveryIngestClient, DiscoveryMachineApiError
from discovery_ingest.enrich import (
    catalogue_export_item_from_machine,
    fim_steckbrief_claim_requests,
    fim_steckbrief_entity_request,
)
from discovery_ingest.fim.models import Steckbrief
from discovery_ingest.schemas import ClaimedTask
from discovery_ingest.worker.fetcher import PoliteUrlFetcher
from discovery_ingest.worker.settle import fail_from_outcome, fail_permanently

_DEFAULT_FIM_BASE = "https://fimportal.de"


def handle_enrich_metadata(
    task: ClaimedTask,
    *,
    client: DiscoveryIngestClient,
    fetcher: PoliteUrlFetcher,
    fim_base_url: str = _DEFAULT_FIM_BASE,
) -> str:
    """Fetch steckbrief JSON and upsert entity and claims via the machine API."""
    try:
        catalogue = client.catalogue.get(task.catalogue_service_id)
    except DiscoveryMachineApiError as err:
        return fail_permanently(client, task.id, err.detail)

    outcome = fetcher.get(task.target_url)
    if outcome.failed:
        return fail_from_outcome(client, task.id, outcome)

    try:
        steckbrief = Steckbrief.from_body(outcome.body)
    except ValueError as err:
        return fail_permanently(client, task.id, str(err))
    if steckbrief is None:
        return fail_permanently(client, task.id, "steckbrief response is not JSON object")

    export_row = catalogue_export_item_from_machine(catalogue)
    entity_body = fim_steckbrief_entity_request(export_row, steckbrief, fim_base_url=fim_base_url)

    try:
        entity = client.catalogue.upsert_entity(entity_body)
        for claim in fim_steckbrief_claim_requests(
            export_row,
            steckbrief,
            entity_id=entity.id,
            fim_base_url=fim_base_url,
        ):
            client.catalogue.append_claim(claim)
    except DiscoveryMachineApiError as err:
        return fail_permanently(client, task.id, err.detail)

    client.tasks.complete(task.id)
    return "completed"
