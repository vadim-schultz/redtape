"""The ``TranslationEngine`` port: what the drain and the probe need from a provider, nothing about candidates or HTTP."""

from __future__ import annotations

from typing import Protocol

from discovery_ingest.translation.units import CallLimits, TranslationBatch, TranslationOutcome, Usage, UsageUnit


class TranslationEngine(Protocol):
    """Translate a batch of units into one locale; every failure is a :class:`TranslationEngineError`."""

    @property
    def name(self) -> str:
        """The registry name of the engine, recorded with every stored translation."""
        ...

    @property
    def usage_unit(self) -> UsageUnit:
        """The unit the engine is billed in."""
        ...

    @property
    def limits(self) -> CallLimits:
        """How many units one call may carry and how many calls may be in flight at once."""
        ...

    def translate(self, batch: TranslationBatch) -> TranslationOutcome:
        """Return one result per unit of ``batch`` in order, or raise a :class:`TranslationEngineError`."""
        ...

    def estimate(self, batch: TranslationBatch) -> Usage:
        """Return the usage to reserve for ``batch``, in :attr:`usage_unit`."""
        ...
