"""Page and record caps for one crawl run, shared by the paginated source clients."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TypeVar

T = TypeVar("T")


@dataclass(slots=True)
class PageBudget:
    """Count the HTTP pages and the records one crawl run may use; ``None`` means no cap of that kind.

    A page cap below one is exhausted before the first fetch, so a run with ``max_pages=0`` makes no request.
    """

    max_pages: int | None
    max_records: int | None = None
    _pages: int = field(default=0, init=False)
    _records: int = field(default=0, init=False)

    @property
    def exhausted(self) -> bool:
        """Return whether the page or the record cap is used up, so no further fetch may start."""
        if self.max_pages is not None and self._pages >= self.max_pages:
            return True
        return self.max_records is not None and self._records >= self.max_records

    def spend_page(self) -> None:
        """Count one HTTP fetch against the page cap."""
        self._pages += 1

    def admit(self, records: Sequence[T]) -> list[T]:
        """Return the leading records that fit the remaining record cap and count them as used."""
        if self.max_records is None:
            kept = list(records)
        else:
            remaining = max(self.max_records - self._records, 0)
            kept = list(records[:remaining])
        self._records += len(kept)
        return kept
