"""Claim embedding tasks, embed them on Workers AI and post the vectors, until the policy or a limit stops the drain."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from discovery_ingest.budget import BudgetGuard
from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.extract.embedding.client import Embedder
from discovery_ingest.extract.embedding.meter import EmbeddingMeter, open_embedding_meter
from discovery_ingest.schemas import DrainReport
from discovery_ingest.worker.drain_loop import Finish, drain_until_stop, monotonic
from discovery_ingest.worker.embed_batch import EmbedContext, run_embed_batch
from discovery_ingest.worker.policy import DrainPolicy
from discovery_ingest.worker.report import build_report, remaining_of
from discovery_ingest.worker.tally import Tally


@dataclass(frozen=True, slots=True)
class EmbedDeps:
    """The machine client, the embedding client and model, and the optional ledger guard and clock of one drain."""

    client: DiscoveryIngestClient
    embedder: Embedder
    model: str
    budget: BudgetGuard | None = None
    clock: Callable[[], float] = monotonic


def _open_meter(deps: EmbedDeps, policy: DrainPolicy, guard: BudgetGuard) -> EmbeddingMeter | None:
    if policy.neuron_budget is None:
        raise ValueError("neuron_budget is required to drain embeddings")
    return open_embedding_meter(policy.neuron_budget, guard, deps.model)


def _close_tally(tally: Tally, meter: EmbeddingMeter, guard: BudgetGuard) -> None:
    tally.neurons_used = round(meter.used_neurons, 1)
    tally.ledger_unavailable = guard.ledger_unavailable


def _report(deps: EmbedDeps, tally: Tally, finish: Finish) -> DrainReport:
    return build_report(tally, finish, remaining_of(lambda: deps.client.embeddings.summary(deps.model).pending_ready))


def run_embed_drain(deps: EmbedDeps, policy: DrainPolicy) -> DrainReport:
    """Claim, embed and complete batches until ``policy`` says to stop; return the report.

    ``policy.neuron_budget`` is required. With no neuron left today the drain stops ``llm_budget`` before it claims
    anything. A quota or budget stop releases the batch in hand, so no attempt is consumed; the report counts a
    ``stale`` vector (the text changed meanwhile) as completed, because the API has queued the new text.
    """
    guard, tally = deps.budget or BudgetGuard(deps.client.budget), Tally()
    meter = _open_meter(deps, policy, guard)
    if meter is None:
        return _report(deps, tally, Finish("llm_budget"))
    ctx = EmbedContext(deps.client, deps.embedder, meter, policy, deps.model)
    finish = drain_until_stop(lambda: run_embed_batch(ctx, tally), policy, deps.clock)
    _close_tally(tally, meter, guard)
    return _report(deps, tally, finish)
