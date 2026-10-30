"""Filter options and ordering of the admin catalogue listing."""

from __future__ import annotations

import enum
from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy import ColumnElement, String, cast, func

from app.features.discovery.pipeline import PipelineStage
from app.models.discovery import CatalogueService, DiscoverySource
from app.shared.list_query import SortOrder

Ordering = tuple[ColumnElement, ...]


class CatalogueSortKey(enum.StrEnum):
    """Public sort fields of the catalogue list."""

    EXTERNAL_ID = "external_id"
    TITLE = "title"
    SOURCE = "source"
    STAGE = "stage"


def _title_expression() -> ColumnElement[str]:
    """Return the lower-cased German, else English, else external-id title used for ordering."""
    german, english = CatalogueService.title_i18n["de"].as_string(), CatalogueService.title_i18n["en"].as_string()
    return func.lower(func.coalesce(german, english, CatalogueService.external_id))


_PRIMARY: Mapping[CatalogueSortKey, ColumnElement] = {
    CatalogueSortKey.EXTERNAL_ID: CatalogueService.external_id.expression,
    CatalogueSortKey.TITLE: _title_expression(),
    CatalogueSortKey.SOURCE: cast(CatalogueService.source, String),
    CatalogueSortKey.STAGE: CatalogueService.pipeline_stage.expression,
}
_NEWEST_FIRST: Ordering = (CatalogueService.updated_at.desc(), CatalogueService.id.desc())


@dataclass(frozen=True, slots=True)
class CatalogueFilter:
    """Optional source, stage and external-id search a catalogue listing is narrowed to, plus its ordering."""

    source: DiscoverySource | None = None
    stage: PipelineStage | None = None
    q: str | None = None
    sort_by: CatalogueSortKey | None = None
    sort_order: SortOrder = SortOrder.ASC

    def conditions(self) -> list[ColumnElement[bool]]:
        """Return the where-clauses of the filters that are set."""
        matches = [] if self.source is None else [CatalogueService.source == self.source]
        if self.stage is not None:
            matches.append(CatalogueService.pipeline_stage == self.stage.value)
        if self.q is None:
            return matches
        return [*matches, CatalogueService.external_id.icontains(self.q, autoescape=True)]

    def ordering(self) -> Ordering:
        """Return the requested key and direction then newest first; newest first alone without a key."""
        if self.sort_by is None:
            return _NEWEST_FIRST
        primary = _PRIMARY[self.sort_by]
        return (primary.desc() if self.sort_order is SortOrder.DESC else primary.asc(), *_NEWEST_FIRST)
