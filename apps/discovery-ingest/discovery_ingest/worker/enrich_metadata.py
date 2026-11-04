"""Handle enrich_metadata discovery tasks (FIM steckbrief to entities/claims)."""

from __future__ import annotations

from discovery_ingest.client import DiscoveryIngestClient, DiscoveryMachineApiError
from discovery_ingest.config import DEFAULT_FIM_PORTAL_URL
from discovery_ingest.enrich import catalogue_export_item_from_machine
from discovery_ingest.fim.models import Steckbrief
from discovery_ingest.operations.enrich import FimMapping, post_enrichment
from discovery_ingest.schemas import ClaimedTask
from discovery_ingest.worker.fetcher import PoliteUrlFetcher
from discovery_ingest.worker.settle import fail_from_outcome, fail_permanently


class EnrichMetadataHandler:
    """The ``enrich_metadata`` task handler bound to the FIM Portal base URL of its drain."""

    def __init__(self, fim_base_url: str) -> None:
        """Keep the portal base URL the entity links are built from."""
        self._fim_base_url = fim_base_url

    def __call__(self, task: ClaimedTask, *, client: DiscoveryIngestClient, fetcher: PoliteUrlFetcher) -> str:
        """Settle ``task`` as :func:`handle_enrich_metadata` does, with this handler's portal base URL."""
        return handle_enrich_metadata(task, client=client, fetcher=fetcher, fim_base_url=self._fim_base_url)


def handle_enrich_metadata(
    task: ClaimedTask,
    *,
    client: DiscoveryIngestClient,
    fetcher: PoliteUrlFetcher,
    fim_base_url: str = DEFAULT_FIM_PORTAL_URL,
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
    try:
        post_enrichment(FimMapping(fim_base_url), export_row, steckbrief, client)
    except DiscoveryMachineApiError as err:
        return fail_permanently(client, task.id, err.detail)

    client.tasks.complete(task.id)
    return "completed"
