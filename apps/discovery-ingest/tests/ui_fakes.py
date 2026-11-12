"""Shared fakes of the UI translation tests: source strings, a scripted translator and a tiny glossary."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from discovery_ingest.i18n.strings import SourceString
from discovery_ingest.translation.glossary import Glossary, GlossaryEntry
from discovery_ingest.translation.units import TranslationBatch, TranslationOutcome, TranslationUnit, Usage

GLOSSARY = Glossary(terms=(GlossaryEntry("Antrag", "заявление"),), keep=("BAföG",))
MODEL = "scripted-model-1"


def source(key: str, english: str, german: str, note: str = "") -> SourceString:
    """One string to translate."""
    return SourceString(key=key, german=german, english=english, note=note)


def prefixed(locale: str, text: str) -> str:
    """The stand-in translation: the German text behind a locale tag, so placeholders and numbers survive."""
    return f"[{locale}] {text}"


class ScriptedTranslator:
    """A :class:`Translator` that tags every German text, except where ``answers`` scripts another reply.

    ``answers`` maps a unit key to the replies for its first, second, ... request; ``errors`` raises on the n-th call.
    """

    repairs = True

    def __init__(
        self,
        answers: Mapping[str, Sequence[str]] | None = None,
        *,
        errors: Mapping[int, Exception] | None = None,
    ) -> None:
        self.batches: list[TranslationBatch] = []
        self._answers = {key: list(replies) for key, replies in (answers or {}).items()}
        self._errors = dict(errors or {})

    def translate(self, batch: TranslationBatch) -> TranslationOutcome:
        """Record the batch; answer it or raise the error scripted for this call."""
        self.batches.append(batch)
        error = self._errors.get(len(self.batches))
        if error is not None:
            raise error
        units = tuple(self._answer(batch.target_locale, unit) for unit in batch.units)
        return TranslationOutcome(units, Usage("neurons", float(len(units))), MODEL)

    def _answer(self, locale: str, unit: TranslationUnit) -> TranslationUnit:
        replies = self._answers.get(unit.key)
        text = replies.pop(0) if replies else prefixed(locale, unit.title)
        return TranslationUnit(unit.key, text, "")

    @property
    def asked_keys(self) -> list[str]:
        """Every unit key requested so far, in order, repairs included."""
        return [unit.key for batch in self.batches for unit in batch.units]
