"""Why an emit item (claim or candidate) is not emitted; a reported outcome, never an error."""

from __future__ import annotations

from collections.abc import Sequence

from app.features.suggestions.handlers import Conflict
from app.schema.discovery.emit import SkipReason


class EmitSkip(Exception):
    """Raised inside an emit flow to turn an item into a skipped result."""

    def __init__(self, reason: SkipReason, conflicts: Sequence[Conflict] = ()) -> None:
        """Record the ``reason`` and the ``conflicts`` behind it."""
        super().__init__(reason)
        self.reason: SkipReason = reason
        self.conflicts: Sequence[Conflict] = conflicts
