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


def _run_batches(
    job: UiJob, translator: Translator, files: TranslationFiles, todo: Sequence[SourceString], progress: _Progress
) -> str | None:
    """Translate ``todo`` batch by batch, writing each; return why the run stopped early, or ``None``."""
    for chunk in _chunks(todo, job.batch_size):
        try:
            result = BatchRun(translator, job.rules(), chunk).run()
        except StopDrain as stop:
            return stop.reason
        progress.add(result)
        if result.accepted:
            files.write(job.locale, progress.done)
    return None


def translate_locale(job: UiJob, translator: Translator, files: TranslationFiles) -> UiReport:
    """Translate the strings ``job.locale`` lacks and return the report.

    Strings already in the locale's files are skipped (a rerun only requests the delta) and keys the sources no longer
    have are dropped. Each batch is written whole after it settled, so a stop (quota, budget) leaves every finished
    batch on disk and nothing of the interrupted one.
    """
    required = expand_plurals(job.sources, job.locale)
    existing = files.read(job.locale)
    progress = _Progress({key: existing[key] for key in (s.key for s in required) if key in existing})
    if progress.done != existing:
        files.write(job.locale, progress.done)
    todo = [string for string in required if string.key not in progress.done]
    stopped = _run_batches(job, translator, files, todo, progress)
    gaps = plural_forms_complete(job.locale, progress.done)
    remaining = len(required) - len(progress.done)
    return UiReport(
        job.locale,
        progress.translated,
        progress.repaired,
        tuple(progress.rejected),
        remaining,
        gaps,
        stopped,
        progress.model,
    )
