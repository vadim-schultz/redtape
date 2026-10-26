"""Why a document candidate is not emitted; a reported outcome, never an error."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from app.features.suggestions.handlers import Conflict

SkipReason = Literal["not_found", "no_mentions", "no_source_url", "invalid_payload", "duplicate", "already_emitted"]


class EmitSkip(Exception):
    """Raised inside the emit flow to turn a candidate into a skipped result."""

    def __init__(self, reason: SkipReason, conflicts: Sequence[Conflict] = ()) -> None:
        """Record the ``reason`` and the ``conflicts`` behind it."""
        super().__init__(reason)
        self.reason: SkipReason = reason
        self.conflicts: Sequence[Conflict] = conflicts
