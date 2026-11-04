"""Canonical list-query allowlist of the admin catalogue listing and its mapping to a ``CatalogueFilter``."""

from __future__ import annotations

from dataclasses import replace

from litestar.params import Parameter

from app.features.discovery.list_query import DiscoveryListQuery
from app.features.discovery.pipeline import PipelineStage
from app.features.discovery.repository import CatalogueFilter, CatalogueSortKey, Page
from app.models.discovery import DiscoverySource
from app.shared.list_query import ListQuery, ListQuerySpec, SortOrder, enum_filter
from app.shared.paging import PageParams

CATALOGUE_LIST_SPEC = ListQuerySpec(
    sort_keys=frozenset(key.value for key in CatalogueSortKey),
    filters={"source": enum_filter(DiscoverySource), "stage": enum_filter(PipelineStage)},
)


def provide_catalogue_query(
    page: PageParams,
    list_query: ListQuery,
    source: DiscoverySource | None = Parameter(query="source", default=None),
) -> DiscoveryListQuery[CatalogueFilter]:
    """Collect the catalogue list parameters, legacy and canonical, into one filter and page."""
    catalogue_filter = catalogue_filter_from(list_query, CatalogueFilter(source=source))
    return DiscoveryListQuery(filters=catalogue_filter, page=Page(offset=page.offset, limit=page.limit))


def catalogue_filter_from(query: ListQuery, legacy: CatalogueFilter) -> CatalogueFilter:
    """Return the filter for ``query``; the canonical source wins over the ``legacy`` one it replaces."""
    narrowed = replace(
        legacy,
        q=query.q,
        source=query.filter_or("source", DiscoverySource, legacy.source),
        stage=query.filter_or("stage", PipelineStage, legacy.stage),
    )
    if query.sort_by is None:
        return narrowed
    return replace(narrowed, sort_by=CatalogueSortKey(query.sort_by), sort_order=query.sort_order or SortOrder.ASC)
