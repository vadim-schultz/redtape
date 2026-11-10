"""Settle the tasks of an embedding batch: record each posted vector's outcome, fail a batch, hand a batch back."""

from __future__ import annotations

import sys
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass

import httpx

from discovery_ingest.client import DiscoveryIngestClient, DiscoveryMachineApiError
from discovery_ingest.embedding_models import ClaimedEmbeddingTask, EmbeddingItemResult, EmbeddingOutcome
from discovery_ingest.worker.release import MAX_REASON
from discovery_ingest.worker.stop import StopDrain
from discovery_ingest.worker.tally import COMPLETED, FAILED, STALE, Tally

HTTP_CONFLICT = 409
SKIPPED = "skipped"
_LABELS: Mapping[EmbeddingOutcome, str] = {"stored": COMPLETED, "stale": STALE, "rejected": FAILED}


@dataclass(frozen=True, slots=True)
class Failure:
    """Why a batch could not be embedded and whether the API should retry its tasks."""

    message: str
    retryable: bool


def _api_stop(err: DiscoveryMachineApiError) -> StopDrain:
    if err.is_database_limit:
        return StopDrain("db_limit", err.detail)
    return StopDrain("error", str(err))


@contextmanager
def refusals_as_stops() -> Iterator[None]:
    """Turn a machine API call that failed into the stop that ends the drain.

    The soft limit is ``db_limit``; any other refusal and any transport failure (the outcome of the call is unknown)
    is ``error``, so the batch in hand is released and the report is still printed.
    """
    try:
        yield
    except DiscoveryMachineApiError as err:
        raise _api_stop(err) from err
    except httpx.HTTPError as err:
        raise StopDrain("error", f"{type(err).__name__}: {err}") from err


def record_results(results: Sequence[EmbeddingItemResult], tally: Tally) -> None:
    """Count one outcome per posted vector; a rejection (including a replayed complete) is logged, never fatal."""
    for result in results:
        tally.record(_LABELS[result.outcome])
        if result.outcome == "rejected":
            print(f"embedding task {result.task_id} rejected: {result.reason}", file=sys.stderr)


def fail_batch(client: DiscoveryIngestClient, tasks: Sequence[ClaimedEmbeddingTask], failure: Failure) -> list[str]:
    """Fail every task of a batch the provider could not embed; return one outcome label per task."""
    return [_fail_one(client, task, failure) for task in tasks]


def _fail_one(client: DiscoveryIngestClient, task: ClaimedEmbeddingTask, failure: Failure) -> str:
    try:
        client.embeddings.fail(task.task_id, error=failure.message, retryable=failure.retryable)
    except DiscoveryMachineApiError as err:
        if err.status_code != HTTP_CONFLICT:
            raise
        print(f"fail of embedding task {task.task_id} refused: {err}", file=sys.stderr)
        return SKIPPED
    return FAILED


def release_batch(client: DiscoveryIngestClient, tasks: Sequence[ClaimedEmbeddingTask], reason: str) -> int:
    """Hand a batch back without consuming an attempt; return how many tasks the API took (a failure is logged)."""
    try:
        answer = client.embeddings.release([task.task_id for task in tasks], reason[:MAX_REASON])
    except (DiscoveryMachineApiError, httpx.HTTPError) as err:
        print(f"release of {len(tasks)} embedding tasks failed: {err}", file=sys.stderr)
        return 0
    return len(answer.released)
