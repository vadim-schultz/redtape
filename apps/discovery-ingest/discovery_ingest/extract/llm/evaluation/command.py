"""``llm eval``: run the gold set through the cleaner, the model and grounding, and report the metrics."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import httpx
from pydantic import ValidationError

from discovery_ingest.api_client import DiscoveryMachineApiError, DiscoveryMachineClient
from discovery_ingest.browser.throttle import Throttle
from discovery_ingest.budget import BudgetGuard
from discovery_ingest.config import IngestSettings, load_ingest_settings
from discovery_ingest.extract.llm.client import LlmClient
from discovery_ingest.extract.llm.cloudflare import CloudflareAiClient
from discovery_ingest.extract.llm.evaluation.arguments import register_eval_parser, startup_problem
from discovery_ingest.extract.llm.evaluation.gold import GoldError, GoldPage, load_gold, unknown_codes
from discovery_ingest.extract.llm.evaluation.report import table_lines
from discovery_ingest.extract.llm.evaluation.report_json import json_report
from discovery_ingest.extract.llm.evaluation.runner import EvalRunner
from discovery_ingest.extract.llm.evaluation.setup import EvalSetup
from discovery_ingest.extract.llm.evaluation.summary import summarise
from discovery_ingest.extract.llm.meter import NeuronMeter, open_neuron_meter
from discovery_ingest.extract.llm.redaction import scrub, secrets_of
from discovery_ingest.extract.llm.taxonomy import Taxonomy

__all__ = ["EvalRuntime", "llm_eval", "register_eval_parser"]

EXIT_STOPPED = 1
EXIT_USAGE = 2
MIN_INTERVAL_SECONDS = 1.0


@dataclass(frozen=True, slots=True)
class EvalRuntime:
    """The three live pieces of a run: the model client, the budget ledger and the tag vocabulary."""

    client: LlmClient
    guard: BudgetGuard
    taxonomy: Taxonomy


def _fail(message: str) -> int:
    print(message, file=sys.stderr)
    return EXIT_USAGE


def _runtime(settings: IngestSettings, model: str) -> EvalRuntime:
    """Build the live pieces; tests replace this function."""
    api = DiscoveryMachineClient(settings.discovery_api_url, settings.discovery_api_key)
    client = CloudflareAiClient(
        settings, model=model, http=httpx.Client(trust_env=True), throttle=Throttle(MIN_INTERVAL_SECONDS)
    )
    return EvalRuntime(client, BudgetGuard(api), api.get_taxonomy())


class EvalCommand:
    """One ``llm eval`` invocation: validate, open the meter, run the pages and write the results."""

    def __init__(self, args: argparse.Namespace, settings: IngestSettings, runtime: EvalRuntime) -> None:
        """Keep the options, the settings and the live pieces."""
        self._args = args
        self._settings = settings
        self._runtime = runtime

    def run(self) -> int:
        """Return 0 when every page ran, 1 when the run stopped early, 2 when it could not start."""
        pages = self._pages()
        meter = self._meter()
        if isinstance(pages, str):
            return _fail(pages)
        if isinstance(meter, str):
            return _fail(meter)
        return self._evaluate(pages, meter)

    def _pages(self) -> list[GoldPage] | str:
        try:
            pages = load_gold(Path(self._args.gold_dir), limit=self._args.limit)
        except GoldError as err:
            return str(err)
        taxonomy = self._runtime.taxonomy
        wrong = {page.name: unknown_codes(page, taxonomy) for page in pages if unknown_codes(page, taxonomy)}
        return f"gold labels use codes outside the taxonomy: {wrong}" if wrong else pages

    def _meter(self) -> NeuronMeter | str:
        meter = open_neuron_meter(self._args.neuron_budget, self._runtime.guard)
        if meter is None:
            return "no neurons are left today according to the ledger; nothing was sent"
        return meter

    def _setup(self) -> EvalSetup:
        settings, args = self._settings, self._args
        return EvalSetup(
            args.model, args.prompt_version, self._runtime.taxonomy, settings.llm_max_tokens, settings.llm_input_chars
        )

    def _evaluate(self, pages: list[GoldPage], meter: NeuronMeter) -> int:
        setup = self._setup()
        run = EvalRunner(self._runtime.client, meter, setup).run(pages)
        summary = summarise(run.pages)
        self._print(table_lines(run, summary, setup))
        if self._args.out:
            self._write(json_report(run, summary, setup))
        return EXIT_STOPPED if run.stopped else 0

    def _print(self, lines: list[str]) -> None:
        secrets = secrets_of(self._settings)
        print("\n".join(scrub(line, secrets) for line in lines))

    def _write(self, report: object) -> None:
        text = scrub(json.dumps(report, ensure_ascii=False, indent=2), secrets_of(self._settings))
        Path(self._args.out).write_text(text + "\n", encoding="utf-8")


def llm_eval(args: argparse.Namespace) -> int:
    """Run the eval; exit 2 for a bad setup, 1 when the run stopped early (budget, quota or token), else 0."""
    try:
        settings = load_ingest_settings()
    except ValidationError as err:
        return _fail(f"missing environment: {', '.join(str(e['loc'][0]) for e in err.errors())}")
    problem = startup_problem(args, settings)
    if problem:
        return _fail(problem)
    try:
        runtime = _runtime(settings, args.model)
    except DiscoveryMachineApiError as err:
        return _fail(f"the Discovery API refused the taxonomy request: {err}")
    return EvalCommand(args, settings, runtime).run()
