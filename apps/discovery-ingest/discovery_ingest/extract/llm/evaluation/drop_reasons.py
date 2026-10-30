"""Which drop reasons are grounding failures (the quote is not on the page) and which are guard drops."""

from __future__ import annotations

from collections.abc import Iterable
from types import MappingProxyType
from typing import Literal

from discovery_ingest.extract.llm.ground_state import DroppedItem

ReasonClass = Literal["grounding", "guard"]

GROUNDING_REASONS = frozenset({"quote", "dependency_quote"})
"""The model quoted text that is not on the page."""
GUARD_REASONS = frozenset(
    {"noise", "data_field", "generic_name", "duplicate", "dependency_duplicate", "dependency_endpoint", "page_kind"}
)
"""The pipeline removed an item whose quote may be fine (not a document, a repeat, a lost endpoint, a non-procedure page)."""

_CLASS_OF: MappingProxyType[str, ReasonClass] = MappingProxyType(
    {**dict.fromkeys(GROUNDING_REASONS, "grounding"), **dict.fromkeys(GUARD_REASONS, "guard")}
)


class UnknownDropReason(ValueError):
    """A drop reason that is in neither class; a new guard must be assigned before the eval can score it."""


def reason_class(reason: str) -> ReasonClass:
    """Return the class of ``reason``; an unlisted reason raises instead of counting as grounded."""
    if reason not in _CLASS_OF:
        raise UnknownDropReason(f"drop reason {reason!r} is not assigned to grounding or guard")
    return _CLASS_OF[reason]


def quote_failures(dropped: Iterable[DroppedItem]) -> int:
    """Return how many of the ``dropped`` items were lost because their quote is not on the page."""
    return sum(reason_class(item.reason) == "grounding" for item in dropped)
