"""``translate drain``: the options of one translation drain, and the run that builds the engine and returns the report."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from discovery_ingest.budget import BudgetGuard
from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.extract.llm.meter import RESOURCE
from discovery_ingest.schemas import DrainReport
from discovery_ingest.translation.engine import TranslationEngine
from discovery_ingest.translation.locale_codes import UnmappedLocaleError
from discovery_ingest.translation.registry import EngineConfig, UnknownEngineError, build_engine
from discovery_ingest.translation.settings import TranslationSettings
from discovery_ingest.translation.subscription_meter import SubscriptionMeter
from discovery_ingest.worker.llm_setup import EXIT_MISSING_SETTINGS, EXIT_NOT_READY, LlmSetupError
from discovery_ingest.worker.policy import DrainPolicy
from discovery_ingest.worker.translate_drain import TranslateDeps, run_translate_drain

TRANSLATE_MIN_INTERVAL_SECONDS = 1.0
DEFAULT_TASKS_PER_BATCH = 10
DEFAULT_NEURON_BUDGET = 2500.0
"""Neurons one run may spend: about 200 cards at 10 to 13 neurons each, with the day's floor kept on top."""
DEFAULT_CONCURRENCY = 2
"""Engine calls in flight at once, when the engine allows it (``claude-code`` allows four; ``llm`` allows one)."""


@dataclass(frozen=True, slots=True)
class TranslateOptions:
    """The bounds of one translation drain as the operator gave them."""

    max_tasks: int = DEFAULT_TASKS_PER_BATCH
    max_batches: int = 1
    time_budget_seconds: float | None = None
    neuron_budget: float = DEFAULT_NEURON_BUDGET
    concurrency: int = DEFAULT_CONCURRENCY

    def policy(self) -> DrainPolicy:
        """Return the validated policy, or raise :class:`ValueError` naming the bound that is out of range."""
        return DrainPolicy(
            max_tasks=self.max_tasks,
            max_batches=self.max_batches,
            time_budget_seconds=self.time_budget_seconds,
            neuron_budget=self.neuron_budget,
            concurrency=self.concurrency,
        )


def build_translation_engine(
    settings: TranslationSettings, http: httpx.Client, min_interval_seconds: float
) -> TranslationEngine:
    """Build the engine ``settings`` names, paced by ``min_interval_seconds``; raise :class:`LlmSetupError` when it cannot start."""
    config = EngineConfig(model=settings.translation_model, http=http, min_interval_seconds=min_interval_seconds)
    try:
        return build_engine(settings.translation_engine, config)
    except (ValueError, UnknownEngineError, UnmappedLocaleError) as err:
        raise LlmSetupError(
            f"translation engine {settings.translation_engine!r} cannot start: {err}", EXIT_MISSING_SETTINGS
        ) from err


def check_neuron_ledger(engine: TranslationEngine, client: DiscoveryIngestClient) -> None:
    """Raise :class:`LlmSetupError` when ``engine`` is billed in neurons and the ledger cannot be read."""
    if engine.usage_unit != "neurons":
        return
    if BudgetGuard(client.budget).remaining(RESOURCE).ledger_unavailable:
        raise LlmSetupError(
            "cannot read the neuron budget ledger (GET /machine/budgets); translate drain will not spend without it",
            EXIT_NOT_READY,
        )


def run_translate(
    options: TranslateOptions, settings: TranslationSettings, client: DiscoveryIngestClient
) -> DrainReport:
    """Build the engine named by ``settings``, check the ledger and run the drain; return its report.

    :class:`LlmSetupError` propagates with its ``exit_code`` (the engine cannot start, the ledger cannot be read);
    :class:`ValueError` names an out-of-range bound; :class:`~discovery_ingest.translation.meter.NoMeterForUnitError` means no meter fits the engine's unit.
    """
    policy = options.policy()
    with httpx.Client(trust_env=True) as http:
        engine = build_translation_engine(settings, http, TRANSLATE_MIN_INTERVAL_SECONDS)
        check_neuron_ledger(engine, client)
        deps = TranslateDeps(
            client,
            engine,
            reserve=settings.query_embed_reserve,
            own_meters={"subscription": SubscriptionMeter()},
        )
        return run_translate_drain(deps, policy)
