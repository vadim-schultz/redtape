"""``i18n translate-ui``: build the engine and the neuron meter, translate one locale, record it in the manifest."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import httpx

from discovery_ingest.budget import BudgetGuard
from discovery_ingest.client import DiscoveryIngestClient, DiscoveryMachineApiError
from discovery_ingest.extract.llm.taxonomy import Taxonomy
from discovery_ingest.i18n.files import Layout, TranslationFiles
from discovery_ingest.i18n.locales import allow_unchanged
from discovery_ingest.i18n.manifest import load_manifest, record_generation, save_manifest
from discovery_ingest.i18n.sources import read_sources
from discovery_ingest.i18n.translate_ui import BATCH_SIZE, UiJob, UiReport, translate_locale
from discovery_ingest.operations.translate_drain import build_translation_engine, check_neuron_ledger
from discovery_ingest.translation.glossary import load_glossary
from discovery_ingest.translation.metered import MeteredTranslator
from discovery_ingest.translation.repair import Translator
from discovery_ingest.translation.settings import TranslationSettings
from discovery_ingest.translation.units import TranslationBatch, TranslationOutcome
from discovery_ingest.worker.llm_setup import EXIT_NOT_READY, LlmSetupError
from discovery_ingest.worker.stop import StopDrain
from discovery_ingest.worker.translate_meter import MeterPlan, open_run_meter

UI_MIN_INTERVAL_SECONDS = 1.0
DEFAULT_NEURON_BUDGET = 3000.0
"""Neurons one run may spend: a few hundred short strings per locale at a few neurons each, with a wide margin."""
MANIFEST_FILE = "review.json"


@dataclass(frozen=True, slots=True)
class TranslateUiRequest:
    """What the operator asked for: a locale, the checkout to read and write, the batch size and the neuron budget."""

    locale: str
    repo_root: Path
    batch_size: int = BATCH_SIZE
    neuron_budget: float = DEFAULT_NEURON_BUDGET


@dataclass(frozen=True, slots=True)
class UiOutcome:
    """The report of the run and the neurons it spent."""

    report: UiReport
    neurons: float

    def as_json(self) -> dict[str, object]:
        """Return the report and the spend as one JSON-ready mapping."""
        return {**asdict(self.report), "neurons": self.neurons}


class _NothingToSpend:
    """A translator for a day that has no neurons above the floor: the first batch stops the run."""

    repairs = False

    def translate(self, batch: TranslationBatch) -> TranslationOutcome:
        """Stop the run before any model call."""
        raise StopDrain("llm_budget", "the day's neurons are at or below the floor kept for query embedding")


def _record(layout: Layout, report: UiReport) -> None:
    """Record the run in the manifest when it generated anything: the locale is machine text until reviewed."""
    if not report.translated:
        return
    path = layout.seed_dir / MANIFEST_FILE
    save_manifest(
        path, record_generation(load_manifest(path), report.locale, model=report.model, generated=report.translated)
    )


def _taxonomy(client: DiscoveryIngestClient) -> Taxonomy:
    try:
        return client.candidates.taxonomy()
    except DiscoveryMachineApiError as err:
        raise LlmSetupError(f"cannot read the taxonomy (GET /machine/taxonomy): {err}", EXIT_NOT_READY) from err


def _job(request: TranslateUiRequest, layout: Layout, client: DiscoveryIngestClient) -> UiJob:
    sources = tuple(read_sources(layout, _taxonomy(client)))
    glossary, allow = load_glossary(request.locale), allow_unchanged(request.locale)
    return UiJob(request.locale, sources, glossary, allow, request.batch_size)


def run_translate_ui(
    request: TranslateUiRequest, settings: TranslationSettings, client: DiscoveryIngestClient
) -> UiOutcome:
    """Translate ``request.locale`` through the engine ``settings`` names, charged to the shared neuron ledger.

    :class:`~discovery_ingest.worker.llm_setup.LlmSetupError` propagates when the engine cannot start or the ledger
    cannot be read; :class:`~discovery_ingest.translation.meter.NoMeterForUnitError` when no meter fits the engine.
    """
    layout = Layout.under(request.repo_root)
    sources = tuple(read_sources(layout, _taxonomy(client)))
    job = UiJob(
        request.locale, sources, load_glossary(request.locale), allow_unchanged(request.locale), request.batch_size
    )
    with httpx.Client(trust_env=True) as http:
        engine = build_translation_engine(settings, http, UI_MIN_INTERVAL_SECONDS)
        check_neuron_ledger(engine, client)
        plan = MeterPlan(BudgetGuard(client.budget), request.neuron_budget, settings.query_embed_reserve, {})
        meter = open_run_meter(engine.usage_unit, plan)
        translator: Translator = _NothingToSpend() if meter is None else MeteredTranslator(engine, meter)
        report = translate_locale(job, translator, TranslationFiles(layout))
    _record(layout, report)
    return UiOutcome(report, 0.0 if meter is None else round(meter.used, 1))
