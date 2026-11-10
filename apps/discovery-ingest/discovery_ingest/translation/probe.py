"""Run the translation probe: translate a fixed sample batch by batch, validate it and project the corpus cost.

The probe writes nothing to the database; the only file it makes is the spot-check sheet, written by the caller.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from dataclasses import dataclass

from discovery_ingest.translation.engine import TranslationEngine
from discovery_ingest.translation.errors import TranslationEngineError, UnusableOutputError
from discovery_ingest.translation.glossary import Glossary
from discovery_ingest.translation.probe_report import ProbeReport
from discovery_ingest.translation.probe_sample import Corpus, pick_sample
from discovery_ingest.translation.probe_sheet import SheetRow
from discovery_ingest.translation.probe_tally import ProbeTally
from discovery_ingest.translation.units import TranslationBatch, TranslationUnit
from discovery_ingest.translation.validate import validate_unit

SOURCE_LOCALE = "de"


@dataclass(frozen=True, slots=True)
class ProbeOptions:
    """One probe run: the locale and its glossary, the sample and batch sizes, the spending cap, the daily budget and the locale count."""

    locale: str
    glossary: Glossary
    sample: int
    batch_size: int
    max_usage: float
    daily_budget: float
    target_count: int


@dataclass(frozen=True, slots=True)
class ProbeResult:
    """The report and the rows of the spot-check sheet."""

    report: ProbeReport
    rows: list[SheetRow]


def _chunks(units: tuple[TranslationUnit, ...], size: int) -> Iterator[tuple[TranslationUnit, ...]]:
    for start in range(0, len(units), size):
        yield units[start : start + size]


def _project(report: ProbeReport, corpus: Corpus, options: ProbeOptions) -> ProbeReport:
    """Add the corpus size and, from the usage per unit, the projected usage and the days it takes at the daily budget."""
    report.corpus_total, report.target_locales = corpus.total, options.target_count
    if report.usage_per_unit is None:
        return report
    report.projected_usage_locale = report.usage_per_unit * corpus.total
    report.projected_usage_all_locales = report.projected_usage_locale * options.target_count
    if report.usage_unit == "neurons":
        report.daily_budget = options.daily_budget
        report.days_at_daily_budget = round(report.projected_usage_all_locales / options.daily_budget, 2)
    return report


class _Run:
    """One probe: the engine, the glossary, the tally and the clock."""

    def __init__(self, engine: TranslationEngine, options: ProbeOptions) -> None:
        self.tally = ProbeTally(engine.usage_unit)
        self.stopped: str | None = None
        self._engine, self._options = engine, options

    def translate(self, chunk: tuple[TranslationUnit, ...]) -> bool:
        """Translate one batch and record it; return whether the probe should go on."""
        batch = TranslationBatch(SOURCE_LOCALE, self._options.locale, chunk, self._options.glossary)
        started = time.monotonic()
        try:
            outcome = self._engine.translate(batch)
        except UnusableOutputError:
            for source in chunk:
                self.tally.add_unusable(source)
            return True
        except TranslationEngineError as err:
            self.stopped = f"{type(err).__name__}: {err}"
            return False
        self.tally.add_batch(outcome.usage, round((time.monotonic() - started) * 1000), outcome.model)
        for source, translated in zip(chunk, outcome.results, strict=True):
            self.tally.add_result(source, translated, validate_unit(source, translated, self._options.glossary))
        return self._within_cap()

    def _within_cap(self) -> bool:
        if self.tally.usage.amount < self._options.max_usage:
            return True
        self.stopped = f"max usage {self._options.max_usage} reached"
        return False


def run_probe(engine: TranslationEngine, corpus: Corpus, options: ProbeOptions) -> ProbeResult:
    """Translate the fixed sample of ``corpus`` with ``engine``, validate it and return the report and the sheet rows."""
    sample = pick_sample(corpus.units, options.sample)
    run = _Run(engine, options)
    for chunk in _chunks(sample, options.batch_size):
        if not run.translate(chunk):
            break
    report = run.tally.report(engine.name, options.locale, len(sample))
    report.stopped = run.stopped
    return ProbeResult(_project(report, corpus, options), run.tally.rows)
