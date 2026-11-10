"""How a candidate list was produced: the one typed value the service decides and every layer reads."""

from __future__ import annotations

import enum


class SearchMode(enum.StrEnum):
    """``browse`` has no query, ``hybrid`` fuses both legs, ``keyword`` is full text alone (flag off or no vector)."""

    BROWSE = "browse"
    HYBRID = "hybrid"
    KEYWORD = "keyword"

    @property
    def legs(self) -> int:
        """How many retrieval legs feed the fusion; relevance is normalised against this many perfect ranks."""
        return 2 if self is SearchMode.HYBRID else 1
