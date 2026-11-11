"""Shared fakes of the translation tests: a recording usage meter and canned batches."""

from __future__ import annotations

from dataclasses import dataclass, field

from discovery_ingest.translation.glossary import Glossary, GlossaryEntry
from discovery_ingest.translation.meter import UsageDenied, UsageReservation
from discovery_ingest.translation.units import TranslationBatch, TranslationUnit, Usage

GLOSSARY = Glossary(terms=(GlossaryEntry("Antrag", "application"),), keep=("SGB II",))


def unit(key: str, title: str, description: str = "") -> TranslationUnit:
    """One unit with a key, a title and a description."""
    return TranslationUnit(key=key, title=title, description=description)


def batch(*units: TranslationUnit, target: str = "en") -> TranslationBatch:
    """A German-to-``target`` batch of ``units`` with the test glossary."""
    return TranslationBatch(source_locale="de", target_locale=target, units=units, glossary=GLOSSARY)


@dataclass
class RecordingMeter:
    """A :class:`UsageMeter` that grants everything and remembers what was reserved, settled and refunded."""

    deny: UsageDenied | None = None
    reserved: list[Usage] = field(default_factory=list)
    settled: list[Usage] = field(default_factory=list)
    refunded: list[Usage] = field(default_factory=list)
    exhausted: bool = False

    def reserve(self, usage: Usage, model: str) -> UsageReservation | UsageDenied:
        """Grant ``usage`` unless ``deny`` is set."""
        if self.deny is not None:
            return self.deny
        self.reserved.append(usage)
        return UsageReservation(usage=usage, model=model, ledgered=False)

    def settle(self, reservation: UsageReservation, actual: Usage) -> None:
        """Remember the actual usage."""
        self.settled.append(actual)

    def refund(self, reservation: UsageReservation) -> None:
        """Remember the refunded reservation."""
        self.refunded.append(reservation.usage)

    def exhaust(self) -> None:
        """Remember that the provider said the allowance is gone."""
        self.exhausted = True

    def remaining(self) -> float | None:
        """Report no known limit."""
        return None

    @property
    def used(self) -> float:
        """Return the usage settled so far."""
        return sum(usage.amount for usage in self.settled)
