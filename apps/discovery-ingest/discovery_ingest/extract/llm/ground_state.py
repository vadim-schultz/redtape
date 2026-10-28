"""What grounding returns and the counters it fills while it works."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field

from discovery_ingest.extract.llm.schema import DependencyItem, DocumentItem


@dataclass(frozen=True, slots=True)
class Diagnostics:
    """Why items were lost: drops per reason, codes outside the vocabulary and nulled URLs."""

    page_kind: str
    dropped: Mapping[str, int]
    unknown_codes: int
    urls_nulled: int


@dataclass(frozen=True, slots=True)
class Grounded:
    """The part of a model answer that quotes the page and fits the vocabulary."""

    documents: tuple[DocumentItem, ...]
    dependencies: tuple[DependencyItem, ...]
    domain_codes: tuple[str, ...]
    situation_codes: tuple[str, ...]
    diagnostics: Diagnostics


@dataclass(slots=True)
class Tally:
    """Mutable counters of one grounding run."""

    dropped: Counter[str] = field(default_factory=Counter)
    unknown_codes: int = 0
    urls_nulled: int = 0

    def drop(self, reason: str, count: int = 1) -> None:
        """Count ``count`` items lost for ``reason``."""
        self.dropped[reason] += count

    def freeze(self, page_kind: str) -> Diagnostics:
        """Return the diagnostics, leaving out reasons that never occurred."""
        dropped = {reason: count for reason, count in self.dropped.items() if count}
        return Diagnostics(page_kind, dropped, self.unknown_codes, self.urls_nulled)
