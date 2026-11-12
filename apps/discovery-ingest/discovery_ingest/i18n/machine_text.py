"""A translator for a machine engine: plural forms go out with a representative number, placeholders as tokens.

The wrapper sits between the interface-string run and the metered engine. Validation still compares each unit with its
own German text (``{count}`` and the named placeholders), because the wrapper restores every text before it returns.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from discovery_ingest.i18n.plural_mt import COUNT, representative_for, restore_count
from discovery_ingest.translation import tokens
from discovery_ingest.translation.repair import Translator
from discovery_ingest.translation.units import TranslationBatch, TranslationOutcome, TranslationUnit


@dataclass(frozen=True, slots=True)
class _Sent:
    """A unit as the engine receives it, and what brings its text back: its sample count and its placeholders."""

    unit: TranslationUnit
    sample: str | None
    placeholders: tuple[str, ...]


def _send(unit: TranslationUnit, locale: str) -> _Sent:
    sample = representative_for(locale, unit.key, unit.title)
    text = unit.title if sample is None else unit.title.replace(COUNT, sample)
    protected, placeholders = tokens.protect(text)
    return _Sent(replace(unit, title=protected), sample, placeholders)


def _receive(sent: _Sent, result: TranslationUnit) -> TranslationUnit:
    text = tokens.restore(restore_count(result.title, sent.sample), sent.placeholders)
    return replace(result, title=text)


class MachineTextTranslator:
    """Translate through ``inner`` an engine that takes text and nothing else: no inflection note, no repair instruction."""

    def __init__(self, inner: Translator) -> None:
        """Keep the translator that makes the calls."""
        self._inner = inner

    @property
    def repairs(self) -> bool:
        """The inner translator's declaration; protecting the text changes no unit's repair."""
        return self._inner.repairs

    def translate(self, batch: TranslationBatch) -> TranslationOutcome:
        """Return the outcome of the inner call, each text restored to its own count and placeholders."""
        sent = [_send(unit, batch.target_locale) for unit in batch.units]
        outcome = self._inner.translate(replace(batch, units=tuple(item.unit for item in sent)))
        if len(outcome.results) != len(sent):
            return outcome
        results = tuple(_receive(item, result) for item, result in zip(sent, outcome.results, strict=True))
        return replace(outcome, results=results)
