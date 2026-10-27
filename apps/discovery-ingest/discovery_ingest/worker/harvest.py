"""Handle harvest_payload discovery tasks: read a stored PVOG payload and record its document mentions."""

from __future__ import annotations

from collections.abc import Sequence

from discovery_ingest.api_client import DiscoveryMachineApiError, DiscoveryMachineClient
from discovery_ingest.harvest.pvog import harvest_pvog_payload
from discovery_ingest.mentions import MentionDraft, MentionItem
from discovery_ingest.schemas import ClaimedTask
from discovery_ingest.worker.fetcher import PoliteUrlFetcher
from discovery_ingest.worker.mention_post import post_mention_chunks
from discovery_ingest.worker.settle import fail_from_api_error


def _items(task: ClaimedTask, drafts: Sequence[MentionDraft]) -> list[MentionItem]:
    return [MentionItem(catalogue_service_id=task.catalogue_service_id, **draft.model_dump()) for draft in drafts]


def handle_harvest_payload(
    task: ClaimedTask,
    *,
    client: DiscoveryMachineClient,
    fetcher: PoliteUrlFetcher,  # shared handler signature; this task needs no network
) -> str:
    """Harvest mentions from the task's catalogue payload, post them in chunks and complete the task."""
    try:
        catalogue = client.get_catalogue(task.catalogue_service_id)
        post_mention_chunks(client, _items(task, harvest_pvog_payload(catalogue.raw_payload)))
    except DiscoveryMachineApiError as err:
        return fail_from_api_error(client, task.id, err)
    client.complete_task(task.id)
    return "completed"
