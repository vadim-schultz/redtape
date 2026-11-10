"""Claim one batch of embedding tasks, embed it under the neuron meter and post the vectors."""

from __future__ import annotations

from dataclasses import dataclass

from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.embedding_models import ClaimedEmbeddingTask, EmbeddingCompleteItem, EmbeddingItemResult
from discovery_ingest.extract.embedding.client import Embedder, EmbeddingResult
from discovery_ingest.extract.embedding.meter import EmbeddingMeter
from discovery_ingest.extract.llm.errors import LlmError
from discovery_ingest.extract.llm.meter import Reservation
from discovery_ingest.worker.batch import BatchResult
from discovery_ingest.worker.embed_refusal import refusal
from discovery_ingest.worker.embed_settle import Failure, fail_batch, record_results, refusals_as_stops, release_batch
from discovery_ingest.worker.llm_answer import denial_reason
from discovery_ingest.worker.policy import DrainPolicy
from discovery_ingest.worker.stop import StopDrain
from discovery_ingest.worker.tally import Tally

Tasks = list[ClaimedEmbeddingTask]


@dataclass(frozen=True, slots=True)
class EmbedContext:
    """Everything one embedding drain shares across batches."""

    client: DiscoveryIngestClient
    embedder: Embedder
    meter: EmbeddingMeter
    policy: DrainPolicy
    model: str


def run_embed_batch(ctx: EmbedContext, tally: Tally) -> BatchResult:
    """Claim one batch and settle it; a stop signal releases the whole batch and ends the drain."""
    tally.batches += 1
    try:
        tasks = _claim(ctx)
    except StopDrain as stop:
        return BatchResult(0, stop)
    tally.claimed += len(tasks)
    return BatchResult(len(tasks), _settle(ctx, tasks, tally))


def _claim(ctx: EmbedContext) -> Tasks:
    with refusals_as_stops():
        return ctx.client.embeddings.claim(ctx.model, limit=ctx.policy.max_tasks).items


def _settle(ctx: EmbedContext, tasks: Tasks, tally: Tally) -> StopDrain | None:
    if not tasks:
        return None
    try:
        with refusals_as_stops():
            _embed_and_complete(ctx, tasks, tally)
    except StopDrain as stop:
        tally.released += release_batch(ctx.client, tasks, f"{stop.reason}: {stop}")
        return stop
    return None


def _embed_and_complete(ctx: EmbedContext, tasks: Tasks, tally: Tally) -> None:
    reservation = _reserve(ctx, tasks)
    tally.llm_calls += 1
    result = _embed(ctx, tasks, reservation, tally)
    if result is not None:
        record_results(_complete(ctx, tasks, result), tally)


def _reserve(ctx: EmbedContext, tasks: Tasks) -> Reservation:
    answer = ctx.meter.reserve([task.text for task in tasks])
    if isinstance(answer, Reservation):
        return answer
    raise StopDrain("llm_budget", denial_reason(answer))


def _embed(ctx: EmbedContext, tasks: Tasks, reservation: Reservation, tally: Tally) -> EmbeddingResult | None:
    """Return the vectors of the batch, or ``None`` after the provider's refusal failed its tasks."""
    try:
        result = ctx.embedder.embed([task.text for task in tasks])
    except LlmError as err:
        _fail_tasks(ctx, tasks, refusal(ctx.meter, reservation, err), tally)
        return None
    ctx.meter.settle(reservation, result)
    return result


def _fail_tasks(ctx: EmbedContext, tasks: Tasks, failure: Failure, tally: Tally) -> None:
    for label in fail_batch(ctx.client, tasks, failure):
        tally.record(label)


def _complete(ctx: EmbedContext, tasks: Tasks, result: EmbeddingResult) -> list[EmbeddingItemResult]:
    items = [
        EmbeddingCompleteItem(task_id=task.task_id, text_hash=task.text_hash, model=ctx.model, vector=list(vector))
        for task, vector in zip(tasks, result.vectors, strict=True)
    ]
    return ctx.client.embeddings.complete(items).items
