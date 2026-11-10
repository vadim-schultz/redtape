"""Settle the tasks of an embedding batch: record each posted vector's outcome."""

from __future__ import annotations

import sys
from collections.abc import Mapping, Sequence

from discovery_ingest.embedding_models import EmbeddingItemResult, EmbeddingOutcome
from discovery_ingest.worker.tally import COMPLETED, FAILED, STALE, Tally

_LABELS: Mapping[EmbeddingOutcome, str] = {"stored": COMPLETED, "stale": STALE, "rejected": FAILED}


def record_results(results: Sequence[EmbeddingItemResult], tally: Tally) -> None:
    """Count one outcome per posted vector; a rejection (including a replayed complete) is logged, never fatal."""
    for result in results:
        tally.record(_LABELS[result.outcome])
        if result.outcome == "rejected":
            print(f"embedding task {result.task_id} rejected: {result.reason}", file=sys.stderr)
