"""The optional narrowing of the suggestion list, passed as one value from the query to SQL."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from app.models.suggestion import SuggestionKind, SuggestionSource, SuggestionStatus


@dataclass(frozen=True)
class SuggestionFilters:
    """Optional narrowing of the suggestion list; an empty `status` means no filter on that axis."""

    status: Sequence[SuggestionStatus] = ()
    kind: SuggestionKind | None = None
    source_type: SuggestionSource | None = None
    jurisdiction_id: UUID | None = None
