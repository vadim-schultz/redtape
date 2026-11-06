"""``llm eval``: run the gold set through the cleaner, the model and grounding, and report the metrics."""

from __future__ import annotations

import json
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path

from discovery_ingest.budget import BudgetGuard
from discovery_ingest.client import DiscoveryIngestClient, DiscoveryMachineApiError
from discovery_ingest.config import IngestSettings
from discovery_ingest.extract.llm.client import LlmClient
from discovery_ingest.extract.llm.evaluation.cache import ResultCache
from discovery_ingest.extract.llm.evaluation.gold import GoldError, GoldPage, load_gold, unknown_codes
from discovery_ingest.extract.llm.evaluation.report import table_lines
from discovery_ingest.extract.llm.evaluation.report_json import json_report
from discovery_ingest.extract.llm.evaluation.runner import EvalRunner
from discovery_ingest.extract.llm.evaluation.setup import EvalSetup
from discovery_ingest.extract.llm.evaluation.summary import summarise
from discovery_ingest.extract.llm.meter import NeuronMeter, open_neuron_meter
from discovery_ingest.extract.llm.prices import known_models
from discovery_ingest.extract.llm.prompt import PROMPT_VERSION
from discovery_ingest.extract.llm.redaction import scrub, secrets_of
from discovery_ingest.extract.llm.taxonomy import Taxonomy
from discovery_ingest.operations.models import build_model_client
from discovery_ingest.pvog.category_mapping import CrosswalkError, MachineCrosswalk

DEFAULT_NEURON_BUDGET = 4000.0
DEFAULT_GOLD_DIR = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "gold"
DEFAULT_CACHE_DIR = Path(".llm-eval-cache")
EXIT_STOPPED = 1
EXIT_USAGE = 2


@dataclass(frozen=True, slots=True)
class EvalOptions:
    """The options of one ``llm eval`` run, as the command line gives them."""

    model: str
    prompt_version: str
    limit: int | None
    out: str | None
    neuron_budget: float
    gold_dir: str
    cache_dir: str


@dataclass(frozen=True, slots=True)
class EvalResult:
    """The scrubbed table lines of a finished run, and whether it stopped before every page ran."""

    lines: list[str]
    stopped: bool


class EvalRefused(Exception):
    """The run could not start, or stopped before any page; ``code`` is the exit code the command returns."""

    def __init__(self, message: str, code: int) -> None:
        """Keep the message for the operator and the exit code."""
        super().__init__(message)
        self.message = message
        self.code = code


@dataclass(frozen=True, slots=True)
class EvalRuntime:
    """The live pieces of a run: the model client, the budget ledger, the tag vocabulary and the crosswalk its legacy labels read."""

    client: LlmClient
    guard: BudgetGuard
    taxonomy: Taxonomy
    crosswalk: MachineCrosswalk


def startup_problem(options: EvalOptions, settings: IngestSettings) -> str | None:
    """Return why the command cannot start (credentials, price row, prompt version), or ``None``."""
    if settings.missing_ai_credentials():
        return f"missing environment: {', '.join(settings.missing_ai_credentials())}"
    if options.model not in known_models():
        return f"no neuron price for model {options.model}; add a row to the price table first"
    if options.prompt_version != PROMPT_VERSION:
        return (
            f"this checkout builds prompt {PROMPT_VERSION}, not {options.prompt_version}; "
            "check out the commit that has it"
        )
    return None


def _runtime(settings: IngestSettings, model: str, stack: ExitStack) -> EvalRuntime:
    """Build the live pieces; tests replace this function.

    The model's HTTP client is entered into ``stack``, so its owner closes it on every exit path.
    """
    api = stack.enter_context(DiscoveryIngestClient.from_settings(settings))
    client = build_model_client(settings, model, stack)
    return EvalRuntime(client, BudgetGuard(api.budget), api.candidates.taxonomy(), api.candidates.crosswalk())


def _pages(options: EvalOptions, runtime: EvalRuntime) -> list[GoldPage] | str:
    try:
        pages = load_gold(Path(options.gold_dir), crosswalk=runtime.crosswalk, limit=options.limit)
    except GoldError as err:
        return str(err)
    taxonomy = runtime.taxonomy
    wrong = {page.name: unknown_codes(page, taxonomy) for page in pages if unknown_codes(page, taxonomy)}
    return f"gold labels use codes outside the taxonomy: {wrong}" if wrong else pages


def _meter(options: EvalOptions, guard: BudgetGuard) -> NeuronMeter | str:
    meter = open_neuron_meter(options.neuron_budget, guard)
    if meter is None:
        return "no neurons are left today according to the ledger; nothing was sent"
    if meter.ledger_unavailable:
        return "the budget ledger is unreachable; eval will not spend neurons without it"
    return meter


def _setup(settings: IngestSettings, options: EvalOptions, taxonomy: Taxonomy) -> EvalSetup:
    return EvalSetup(
        options.model,
        options.prompt_version,
        taxonomy,
        settings.llm_max_tokens,
        settings.llm_input_chars,
        options.neuron_budget,
    )


def _evaluate(
    settings: IngestSettings,
    options: EvalOptions,
    runtime: EvalRuntime,
    pages: list[GoldPage],
    meter: NeuronMeter,
) -> EvalResult:
    setup = _setup(settings, options, runtime.taxonomy)
    cache = ResultCache(Path(options.cache_dir))
    run = EvalRunner(runtime.client, meter, setup, cache).run(pages)
    summary = summarise(run.pages)
    secrets = secrets_of(settings)
    if options.out:
        text = scrub(json.dumps(json_report(run, summary, setup), ensure_ascii=False, indent=2), secrets)
        Path(options.out).write_text(text + "\n", encoding="utf-8")
    return EvalResult([scrub(line, secrets) for line in table_lines(run, summary, setup)], bool(run.stopped))


def run_eval(settings: IngestSettings, options: EvalOptions) -> EvalResult:
    """Run the gold set; raise :class:`EvalRefused` when the run cannot start or stops before any page."""
    with ExitStack() as stack:
        try:
            runtime = _runtime(settings, options.model, stack)
        except (DiscoveryMachineApiError, CrosswalkError) as err:
            raise EvalRefused(f"the Discovery API refused the taxonomy request: {err}", EXIT_USAGE) from err
        pages = _pages(options, runtime)
        meter = _meter(options, runtime.guard)
        if isinstance(pages, str):
            raise EvalRefused(pages, EXIT_USAGE)
        if isinstance(meter, str):
            raise EvalRefused(meter, EXIT_STOPPED)
        return _evaluate(settings, options, runtime, pages, meter)
