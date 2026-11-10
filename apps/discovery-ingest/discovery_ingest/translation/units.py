"""The DTOs of the translation core: a unit, a batch of units for one target locale, and what an engine returns."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from discovery_ingest.translation.glossary import Glossary

UsageUnit = Literal["neurons", "characters"]
"""What an engine is billed in; the drain meters through the :class:`UsageMeter` chosen by this unit."""


@dataclass(frozen=True, slots=True)
class Usage:
    """An amount of one billing unit."""

    unit: UsageUnit
    amount: float

    def plus(self, other: Usage) -> Usage:
        """Return the sum with ``other``, which must be in the same unit."""
        if other.unit != self.unit:
            raise ValueError(f"cannot add {other.unit} to {self.unit}")
        return Usage(self.unit, self.amount + other.amount)


@dataclass(frozen=True, slots=True)
class TranslationUnit:
    """One piece of text to translate, or its translation: an opaque ``key``, a title and a description."""

    key: str
    title: str
    description: str


@dataclass(frozen=True, slots=True)
class Correction:
    """The rules an earlier translation of the unit with this ``key`` broke, for the repair request."""

    key: str
    problems: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TranslationBatch:
    """Units that go to one target locale in one call, with the glossary of that locale.

    ``corrections`` is empty for a first translation; a repair request lists, per unit, the rules it must now keep.
    """

    source_locale: str
    target_locale: str
    units: tuple[TranslationUnit, ...]
    glossary: Glossary
    corrections: tuple[Correction, ...] = ()


@dataclass(frozen=True, slots=True)
class TranslationOutcome:
    """One result per unit in the order of the batch, what the call cost, and the model that made it (``None`` if none)."""

    results: tuple[TranslationUnit, ...]
    usage: Usage
    model: str | None
