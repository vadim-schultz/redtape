"""``translate drain``: the options of one translation drain, and the run that builds the engine and returns the report."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

import httpx

from discovery_ingest.budget import BudgetGuard
from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.schemas import DrainReport
from discovery_ingest.translation.engine import TranslationEngine
from discovery_ingest.translation.locale_codes import UnmappedLocaleError
from discovery_ingest.translation.meter import LEDGER_RESOURCE
from discovery_ingest.translation.registry import EngineConfig, UnknownEngineError, build_engine
from discovery_ingest.translation.settings import TranslationSettings
from discovery_ingest.translation_models import PriorityBand
from discovery_ingest.worker.llm_setup import EXIT_MISSING_SETTINGS, EXIT_NOT_READY, LlmSetupError
from discovery_ingest.worker.policy import DrainPolicy
from discovery_ingest.worker.run import run_recorded
from discovery_ingest.worker.translate_drain import TranslateDeps, run_translate_drain
from discovery_ingest.worker.translate_meter import own_meters_for

TRANSLATE_MIN_INTERVAL_SECONDS = 1.0
DEFAULT_TASKS_PER_BATCH = 10
DEFAULT_NEURON_BUDGET = 2500.0
"""Neurons one run may spend: about 200 cards at 10 to 13 neurons each, with the day's floor kept on top."""
DEFAULT_CONCURRENCY = 2
"""Engine calls in flight at once, when the engine allows it (``claude-code`` allows four; ``llm`` allows one)."""


@dataclass(frozen=True, slots=True)
class TranslateOptions:
    """The bounds of one translation drain as the operator gave them, the engine it runs on (``None``: ``TRANSLATION_ENGINE``) and its priority band."""

    max_tasks: int = DEFAULT_TASKS_PER_BATCH
    max_batches: int = 1
    time_budget_seconds: float | None = None
    neuron_budget: float = DEFAULT_NEURON_BUDGET
    concurrency: int = DEFAULT_CONCURRENCY
    engine: str | None = None
    band: PriorityBand = field(default_factory=PriorityBand)

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


def check_ledger(engine: TranslationEngine, guard: BudgetGuard) -> None:
    """Raise :class:`LlmSetupError` when the ledger of ``engine``'s unit cannot be read; a unit with no ledger is skipped."""
    resource = LEDGER_RESOURCE.get(engine.usage_unit)
    if resource is None:
        return
    if guard.remaining(resource).ledger_unavailable:
        raise LlmSetupError(
            f"cannot read the {resource} budget ledger (GET /machine/budgets); translate drain will not spend without it",
            EXIT_NOT_READY,
        )


def _drain_deps(
    client: DiscoveryIngestClient, engine: TranslationEngine, settings: TranslationSettings
) -> TranslateDeps:
    """Check the ledger of ``engine``'s unit, then build the drain's dependencies: the engine's own meter, if it has one, and the glossary mode."""
    guard = BudgetGuard(client.budget)
    check_ledger(engine, guard)
    return TranslateDeps(
        client,
        engine,
        reserve=settings.query_embed_reserve,
        own_meters=own_meters_for(engine.usage_unit, guard),
        budget=guard,
        glossary=settings.translation_glossary_mode,
    )


def _with_engine(settings: TranslationSettings, engine: str | None) -> TranslationSettings:
    """Return ``settings`` with ``engine`` in place of ``TRANSLATION_ENGINE`` when one was named; the name is checked by the caller."""
    return settings if engine is None else settings.model_copy(update={"translation_engine": engine})


def run_translate(
    options: TranslateOptions, settings: TranslationSettings, client: DiscoveryIngestClient
) -> DrainReport:
    """Build the engine the options or ``settings`` name and check its ledger, then run the drain as a ``translate`` run.

    The engine and the ledger are checked before the run opens: :class:`LlmSetupError` (the engine cannot start, the
    ledger cannot be read) propagates with its ``exit_code``. :class:`ValueError` names an out-of-range bound;
    :class:`~discovery_ingest.translation.meter.NoMeterForUnitError` means no meter fits the engine's unit. The claims
    name that engine and take ``options.band``.
    """
    policy, chosen = options.policy(), _with_engine(settings, options.engine)
    with httpx.Client(trust_env=True) as http:
        engine = build_translation_engine(chosen, http, TRANSLATE_MIN_INTERVAL_SECONDS)
        deps = replace(_drain_deps(client, engine, chosen), band=options.band)
        return run_recorded(client, "translate", lambda: run_translate_drain(deps, policy))
