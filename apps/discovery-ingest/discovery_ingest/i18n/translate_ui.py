"""Translate the interface strings of one locale: in batches, resumable, written after every batch."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field

from discovery_ingest.i18n.batch import BatchResult, BatchRules, BatchRun, Rejection
from discovery_ingest.i18n.files import TranslationFiles
from discovery_ingest.i18n.plural import expand_plurals
from discovery_ingest.i18n.strings import SourceString
from discovery_ingest.i18n.validate_ui import plural_forms_complete
from discovery_ingest.translation.glossary import Glossary
from discovery_ingest.translation.repair import Translator
from discovery_ingest.worker.stop import StopDrain

BATCH_SIZE = 40


@dataclass(frozen=True, slots=True)
class UiJob:
    """One locale to translate: its sources, the glossary, the strings that may stay English and the batch size."""

    locale: str
    sources: tuple[SourceString, ...]
    glossary: Glossary
    allow: frozenset[str]
    batch_size: int = BATCH_SIZE

    def rules(self) -> BatchRules:
        """Return what each batch is checked against."""
        return BatchRules(self.locale, self.glossary, self.allow)


@dataclass(frozen=True, slots=True)
class UiReport:
    """What a run did: strings written, repaired, rejected and still absent, the plural gaps, why it stopped and the model."""

    locale: str
    translated: int
    repaired: int
    rejected: tuple[Rejection, ...]
    remaining: int
    gaps: list[str]
    stopped: str | None
    model: str | None


@dataclass
class _Progress:
    """The running totals of one locale: what is written, and what the batches so far did."""

    done: dict[str, str]
    translated: int = 0
    repaired: int = 0
    rejected: list[Rejection] = field(default_factory=list)
    model: str | None = None

    def add(self, result: BatchResult) -> None:
        """Fold one batch's verdicts into the totals."""
        self.done |= result.accepted
        self.translated += len(result.accepted)
        self.repaired += result.repaired
        self.rejected.extend(result.rejected)
        self.model = result.model or self.model


def _chunks(strings: Sequence[SourceString], size: int) -> Iterator[Sequence[SourceString]]:
    for start in range(0, len(strings), size):
        yield strings[start : start + size]


class LocaleRun:
    """One locale through one translator: prune, translate what is missing batch by batch, report."""

    def __init__(self, job: UiJob, translator: Translator, files: TranslationFiles) -> None:
        """Keep the job, the translator and the files, and read what the locale already has."""
        self._job = job
        self._translator = translator
        self._files = files
        self._required = expand_plurals(job.sources, job.locale)
        existing = files.read(job.locale)
        self._progress = _Progress({s.key: existing[s.key] for s in self._required if s.key in existing})
        self._pruned = self._progress.done != existing

    def run(self) -> UiReport:
        """Translate the strings the locale lacks and return the report."""
        if self._pruned:
            self._files.write(self._job.locale, self._progress.done)
        stopped = self._translate_missing()
        return self._report(stopped)

    def _translate_missing(self) -> str | None:
        """Translate the missing strings batch by batch, writing each; return why the run stopped early, or ``None``."""
        missing = [string for string in self._required if string.key not in self._progress.done]
        for chunk in _chunks(missing, self._job.batch_size):
            try:
                result = BatchRun(self._translator, self._job.rules(), chunk).run()
            except StopDrain as stop:
                return stop.reason
            self._settle(result)
        return None

    def _settle(self, result: BatchResult) -> None:
        self._progress.add(result)
        if result.accepted:
            self._files.write(self._job.locale, self._progress.done)

    def _report(self, stopped: str | None) -> UiReport:
        done = self._progress
        gaps = plural_forms_complete(self._job.locale, done.done)
        remaining = len(self._required) - len(done.done)
        return UiReport(
            self._job.locale, done.translated, done.repaired, tuple(done.rejected), remaining, gaps, stopped, done.model
        )


def translate_locale(job: UiJob, translator: Translator, files: TranslationFiles) -> UiReport:
    """Translate the strings ``job.locale`` lacks and return the report.

    Strings already in the locale's files are skipped (a rerun only requests the delta) and keys the sources no longer
    have are dropped. Each batch is written whole after it settled, so a stop (quota, budget) leaves every finished
    batch on disk and nothing of the interrupted one.
    """
    return LocaleRun(job, translator, files).run()
