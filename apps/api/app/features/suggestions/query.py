"""Query-string DTO for the suggestion list endpoint."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from litestar.params import Parameter

from app.features.suggestions.service import SuggestionFilters
from app.models.suggestion import SuggestionKind, SuggestionSource, SuggestionStatus
from app.shared.paging import PageParams


@dataclass(frozen=True, slots=True)
class SuggestionListQuery:
    """Filters plus paging for `GET /suggestions`."""

    filters: SuggestionFilters
    page: PageParams


def provide_suggestion_list_query(
    page: PageParams,
    status: list[SuggestionStatus] | None = Parameter(query="status", default=None),
    kind: SuggestionKind | None = Parameter(query="kind", default=None),
    source_type: SuggestionSource | None = Parameter(query="source_type", default=None),
    jurisdiction_id: UUID | None = Parameter(query="jurisdiction_id", default=None),
) -> SuggestionListQuery:
    """Collect the suggestion list query parameters into one object."""
    filters = SuggestionFilters(
        status=tuple(status or ()), kind=kind, source_type=source_type, jurisdiction_id=jurisdiction_id
    )
    return SuggestionListQuery(filters=filters, page=page)
