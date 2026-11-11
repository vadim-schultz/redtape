"""The DTOs of the translation core: a unit, a batch of units for one target locale, and what an engine returns."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from discovery_ingest.translation.glossary import Glossary

UsageUnit = Literal["neurons", "characters", "subscription"]
"""What an engine is billed in: Workers AI neurons, provider characters, or the tokens of a Claude Code allowance.

The drain meters through the :class:`UsageMeter` chosen by this unit; a ``subscription`` engine brings its own meter and
is never charged to the neuron ledger.
"""


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
class CallLimits:
    """How an engine's calls are cut: the most units one call carries, and how many calls may be in flight at once."""

    units_per_call: int
    concurrency: int


@dataclass(frozen=True, slots=True)
class TranslationUnit:
    """One piece of text to translate, or its translation: an opaque ``key``, a title and a description.

    ``context`` is read-only background for the translator (where the text appears, another language of it); it is
    never translated and never part of a result.
    """

    key: str
    title: str
    description: str
    context: str = ""


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
    """One result per unit in the order of the batch, what the call cost, and the model that made it.

    ``model`` is ``None`` if the provider named none. ``auth`` says how the call was authenticated; it is ``None`` when
    the provider has no login mode (an API key, for example).
    """

    results: tuple[TranslationUnit, ...]
    usage: Usage
    model: str | None
    auth: str | None = None
