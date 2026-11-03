"""The after_snapshot action that queues extract_page when a registered extractor applies to the snapshot."""

from __future__ import annotations

import sys
from collections.abc import Sequence

import httpx
from pydantic import ValidationError

from discovery_ingest.artifacts import ArtifactRead
from discovery_ingest.client import DiscoveryIngestClient, DiscoveryMachineApiError
from discovery_ingest.extract.base import Extractor
from discovery_ingest.extract.registry import find_extractor
from discovery_ingest.schemas import ClaimedTask, TaskEnqueueRequest

EXTRACT_PRIORITY = 100


class ExtractEnqueuer:
    """An :data:`~discovery_ingest.worker.render.AfterSnapshot` hook: one task per snapshot and extractor version."""

    def __init__(self, client: DiscoveryIngestClient, extractors: Sequence[Extractor]) -> None:
        """Enqueue through ``client`` for pages that ``extractors`` match."""
        self._client = client
        self._extractors = extractors

    def __call__(self, task: ClaimedTask, artifact: ArtifactRead) -> None:
        """Enqueue ``extract_page`` for ``artifact``; no match enqueues nothing, an error is logged and never raised."""
        extractor = find_extractor(artifact.source_url, artifact.content_type, self._extractors)
        if extractor is None:
            return
        try:
            self._client.tasks.enqueue(_request(extractor, artifact))
        except (DiscoveryMachineApiError, httpx.HTTPError, ValidationError) as err:
            print(f"extract enqueue failed for {artifact.source_url}: {err}", file=sys.stderr)


def _request(extractor: Extractor, artifact: ArtifactRead) -> TaskEnqueueRequest:
    return TaskEnqueueRequest(
        catalogue_service_id=artifact.catalogue_service_id,
        kind="extract_page",
        target_url=artifact.source_url,
        priority=EXTRACT_PRIORITY,
        input_key=f"{extractor.id}@{extractor.version}",
        artifact_id=artifact.id,
    )
