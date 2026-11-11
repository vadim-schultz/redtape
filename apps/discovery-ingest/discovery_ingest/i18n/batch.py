"""Translate one batch of interface strings: ask, check, repair once and settle each string as accepted or rejected."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from discovery_ingest.i18n.strings import SourceString
from discovery_ingest.i18n.validate_ui import interface_findings
from discovery_ingest.translation.errors import TranslationEngineError
from discovery_ingest.translation.glossary import Glossary
from discovery_ingest.translation.repair import Checked, Translator, check_outcome, repair_batch
from discovery_ingest.translation.units import TranslationBatch

SOURCE_LOCALE = "de"


@dataclass(frozen=True, slots=True)
class Rejection:
    """A string that was left out: its key and each broken rule in words."""

    key: str
    problems: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BatchRules:
    """What a batch is translated and checked against: the target locale, its glossary and the unchanged-text allow list."""

    locale: str
    glossary: Glossary
    allow: frozenset[str]


@dataclass(frozen=True, slots=True)
class BatchResult:
    """The accepted translations by key, the rejections, how many strings the repair rescued and the model."""

    accepted: dict[str, str]
    rejected: tuple[Rejection, ...]
    repaired: int = 0
    model: str | None = None


def _problems(item: Checked) -> tuple[str, ...]:
    return tuple(f"{finding.check}: {finding.detail}" for finding in item.findings)


class BatchRun:
    """One batch through one translator: the first request, at most one repair request, then the verdict per string."""

    def __init__(self, translator: Translator, rules: BatchRules, strings: Sequence[SourceString]) -> None:
        """Keep the translator, the rules and the strings of the batch (by key, for the interface checks)."""
        self._translator = translator
        self._rules = rules
        self._strings = {string.key: string for string in strings}
        self._batch = TranslationBatch(
            SOURCE_LOCALE, rules.locale, tuple(string.unit() for string in strings), rules.glossary
        )

    def run(self) -> BatchResult:
        """Return the verdicts; a batch the engine fails (not a quota or budget stop, which propagates) is rejected whole."""
        try:
            first = self._ask(self._batch)
        except TranslationEngineError as err:
            return self._failed(err)
        retried = self._repair([item for item in first if not item.valid])
        return self._verdicts([item for item in first if item.valid], retried)

    def _ask(self, batch: TranslationBatch) -> list[Checked]:
        checked = check_outcome(batch, self._translator.translate(batch))
        return [self._with_interface_findings(item) for item in checked]

    def _with_interface_findings(self, item: Checked) -> Checked:
        extra = interface_findings(self._strings[item.source.key], item.translated.title, self._rules.allow)
        return Checked(item.source, item.translated, (*item.findings, *extra), item.model)

    def _repair(self, failed: list[Checked]) -> list[Checked]:
        """Ask once more for the failed strings; if that request fails too, they stay as they were."""
        if not failed:
            return []
        try:
            return self._ask(repair_batch(self._batch, failed))
        except TranslationEngineError:
            return failed

    @staticmethod
    def _verdicts(kept: list[Checked], retried: list[Checked]) -> BatchResult:
        everything = [*kept, *retried]
        accepted = {item.source.key: item.translated.title for item in everything if item.valid}
        rejected = tuple(Rejection(item.source.key, _problems(item)) for item in everything if not item.valid)
        models = [item.model for item in everything if item.model]
        rescued = sum(1 for item in retried if item.valid)
        return BatchResult(accepted, rejected, rescued, models[-1] if models else None)

    def _failed(self, err: TranslationEngineError) -> BatchResult:
        reason = (f"the engine failed this batch: {err}",)
        return BatchResult({}, tuple(Rejection(key, reason) for key in self._strings))
