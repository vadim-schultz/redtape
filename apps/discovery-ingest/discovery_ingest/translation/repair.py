"""Check a translation outcome and repair what failed: one more request that states the violated rules, never a loop."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from discovery_ingest.translation.errors import UnusableOutputError
from discovery_ingest.translation.findings import Finding
from discovery_ingest.translation.units import Correction, TranslationBatch, TranslationOutcome, TranslationUnit
from discovery_ingest.translation.validate import validate_unit


class Translator(Protocol):
    """Anything that translates a batch: an engine, or an engine under a meter."""

    def translate(self, batch: TranslationBatch) -> TranslationOutcome:
        """Return one result per unit of ``batch`` in order, or raise."""
        ...


@dataclass(frozen=True, slots=True)
class Checked:
    """A source unit, its translation, the findings of the validators and the model that made it (valid without findings)."""

    source: TranslationUnit
    translated: TranslationUnit
    findings: tuple[Finding, ...]
    model: str | None = None

    @property
    def valid(self) -> bool:
        """Whether the translation keeps every promise the validators check."""
        return not self.findings

    def problems(self) -> tuple[str, ...]:
        """Say each broken rule in words, naming the field it was found in."""
        return tuple(f"{finding.field}: {finding.detail}" for finding in self.findings)


def _answered_in_order(batch: TranslationBatch, outcome: TranslationOutcome) -> None:
    asked = [unit.key for unit in batch.units]
    answered = [unit.key for unit in outcome.results]
    if asked != answered:
        raise UnusableOutputError(f"the engine answered {len(answered)} of {len(asked)} units or in another order")


def check_outcome(batch: TranslationBatch, outcome: TranslationOutcome) -> list[Checked]:
    """Validate every translated unit of ``outcome`` against its source.

    Raises :class:`UnusableOutputError` when the results are not one per unit in the order of ``batch``: a short
    answer fails the batch, it is never paired up by position.
    """
    _answered_in_order(batch, outcome)
    return [
        Checked(source, translated, tuple(validate_unit(source, translated, batch.glossary)), outcome.model)
        for source, translated in zip(batch.units, outcome.results, strict=True)
    ]


def repair_batch(batch: TranslationBatch, failed: Sequence[Checked]) -> TranslationBatch:
    """Return a batch of only the ``failed`` units, each with the rules its first translation broke."""
    corrections = tuple(Correction(item.source.key, item.problems()) for item in failed)
    units = tuple(item.source for item in failed)
    return TranslationBatch(batch.source_locale, batch.target_locale, units, batch.glossary, corrections)


def repair_once(translator: Translator, batch: TranslationBatch, failed: Sequence[Checked]) -> list[Checked]:
    """Ask once more for the ``failed`` units and return them checked again, in the same order.

    A unit that still fails comes back invalid: the caller settles it, nothing asks a third time. Any engine error
    propagates.
    """
    asked = repair_batch(batch, failed)
    return check_outcome(asked, translator.translate(asked))
