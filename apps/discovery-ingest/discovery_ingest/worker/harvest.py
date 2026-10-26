"""Handle harvest_payload discovery tasks: read a stored PVOG payload and record its document mentions."""

from __future__ import annotations

from collections.abc import Iterator, Sequence

from discovery_ingest.api_client import DiscoveryMachineApiError, DiscoveryMachineClient
from discovery_ingest.harvest.pvog import harvest_pvog_payload
from discovery_ingest.mentions import MAX_MENTION_ITEMS, MentionDraft, MentionItem
from discovery_ingest.schemas import ClaimedTask
from discovery_ingest.worker.fetcher import PoliteUrlFetcher
from discovery_ingest.worker.settle import fail_from_api_error


def _chunks(items: Sequence[MentionItem]) -> Iterator[Sequence[MentionItem]]:
    for start in range(0, len(items), MAX_MENTION_ITEMS):
        yield items[start : start + MAX_MENTION_ITEMS]


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
        for chunk in _chunks(_items(task, harvest_pvog_payload(catalogue.raw_payload))):
            client.post_mentions(chunk)
    except DiscoveryMachineApiError as err:
        return fail_from_api_error(client, task.id, err)
    client.complete_task(task.id)
    return "completed"
