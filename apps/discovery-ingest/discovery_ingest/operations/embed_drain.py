"""``embed drain``: the options of one embedding drain, and the run that prepares the embedder and returns the report."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from discovery_ingest.browser.throttle import Throttle
from discovery_ingest.budget import BudgetGuard
from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.config import IngestSettings
from discovery_ingest.extract.embedding.client import EMBED_BATCH_LIMIT, CloudflareEmbeddingClient
from discovery_ingest.extract.llm.meter import RESOURCE
from discovery_ingest.schemas import DrainReport
from discovery_ingest.worker.embed_drain import EmbedDeps, run_embed_drain
from discovery_ingest.worker.llm_setup import EXIT_MISSING_SETTINGS, EXIT_NOT_READY, LlmSetupError
from discovery_ingest.worker.policy import DrainPolicy
from discovery_ingest.worker.run import run_recorded

EMBED_MIN_INTERVAL_SECONDS = 0.2
DEFAULT_NEURON_BUDGET = 3000.0
"""Neurons one run may spend: about 2,700 texts of 1,500 characters, a third of the day's 9,500."""


@dataclass(frozen=True, slots=True)
class EmbedOptions:
    """The bounds of one embedding drain as the operator gave them."""

    max_tasks: int = EMBED_BATCH_LIMIT
    max_batches: int = 1
    time_budget_seconds: float | None = None
    neuron_budget: float = DEFAULT_NEURON_BUDGET

    def policy(self) -> DrainPolicy:
        """Return the validated policy, or raise :class:`ValueError` naming the bound that is out of range."""
        return DrainPolicy(
            max_tasks=self.max_tasks,
            max_batches=self.max_batches,
            time_budget_seconds=self.time_budget_seconds,
            neuron_budget=self.neuron_budget,
        )


def _check_credentials(settings: IngestSettings) -> None:
    missing = settings.missing_ai_credentials()
    if missing:
        raise LlmSetupError(
            f"embed drain needs these environment variables: {', '.join(missing)}", EXIT_MISSING_SETTINGS
        )


def _check_ledger(client: DiscoveryIngestClient) -> None:
    if BudgetGuard(client.budget).remaining(RESOURCE).ledger_unavailable:
        raise LlmSetupError(
            "cannot read the neuron budget ledger (GET /machine/budgets); embed drain will not spend without it",
            EXIT_NOT_READY,
        )


def run_embed(options: EmbedOptions, settings: IngestSettings, client: DiscoveryIngestClient) -> DrainReport:
    """Check the credentials and the ledger, then run the drain as an ``embed`` run and return its report.

    The checks come first: a refusal before the drain starts opens no run. :class:`LlmSetupError` propagates with its
    ``exit_code``; :class:`ValueError` names an out-of-range bound.
    """
    policy = options.policy()
    _check_credentials(settings)
    _check_ledger(client)
    return run_recorded(client, "embed", lambda: _drain(settings, client, policy))


def _drain(settings: IngestSettings, client: DiscoveryIngestClient, policy: DrainPolicy) -> DrainReport:
    with httpx.Client(trust_env=True) as http:
        embedder = CloudflareEmbeddingClient(settings, http=http, throttle=Throttle(EMBED_MIN_INTERVAL_SECONDS))
        return run_embed_drain(EmbedDeps(client, embedder, settings.embedding_model), policy)
