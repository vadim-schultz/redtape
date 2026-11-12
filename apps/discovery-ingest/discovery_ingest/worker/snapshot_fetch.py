"""Fetch a claimed page's stored snapshot through the machine API; release a task whose snapshot was pruned.

A pruned snapshot is not the page's fault and not an attempt: the task goes back with ``snapshot_gone``, and the next
claim stamps the newest snapshot of the row.
"""

from __future__ import annotations

from uuid import UUID

from discovery_ingest.client import DiscoveryMachineApiError
from discovery_ingest.client.artifacts_api import ArtifactsAPI
from discovery_ingest.extract.decode import decode_html
from discovery_ingest.schemas import ClaimedSnapshotTask
from discovery_ingest.worker.snapshot_settle import PageSettler

HTTP_NOT_FOUND = 404
SNAPSHOT_GONE = "snapshot_gone"


class SnapshotGone(Exception):
    """The snapshot a task names was pruned: its artifact answered 404."""


def fetch_page(artifacts: ArtifactsAPI, artifact_id: UUID) -> str:
    """Return the stored HTML of ``artifact_id``, decoded; raise :class:`SnapshotGone` when the API has no such artifact."""
    try:
        content = artifacts.content(artifact_id)
    except DiscoveryMachineApiError as err:
        if err.status_code == HTTP_NOT_FOUND:
            raise SnapshotGone(str(err)) from err
        raise
    return decode_html(content.data, content.content_type)


def release_pruned(settler: PageSettler, task: ClaimedSnapshotTask) -> None:
    """Count a pruned snapshot and hand its task back without an attempt."""
    settler.tally.pruned += 1
    settler.release(task, SNAPSHOT_GONE)
