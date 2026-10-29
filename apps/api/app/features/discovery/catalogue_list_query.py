"""Canonical list-query allowlist of the admin catalogue listing and its mapping to a ``CatalogueFilter``."""

from __future__ import annotations

from dataclasses import replace

from app.features.discovery.repository import CatalogueFilter, CatalogueSortKey
from app.models.discovery import DiscoverySource
from app.shared.list_query import ListQuery, ListQuerySpec, SortOrder, enum_filter

CATALOGUE_LIST_SPEC = ListQuerySpec(
    sort_keys=frozenset(key.value for key in CatalogueSortKey),
    filters={"source": enum_filter(DiscoverySource)},
)


def catalogue_filter_from(query: ListQuery, legacy: CatalogueFilter) -> CatalogueFilter:
    """Return the filter for ``query``; the canonical source wins over the ``legacy`` one it replaces."""
    narrowed = replace(legacy, q=query.q, source=query.filter_or("source", DiscoverySource, legacy.source))
    if query.sort_by is None:
        return narrowed
    return replace(narrowed, sort_by=CatalogueSortKey(query.sort_by), sort_order=query.sort_order or SortOrder.ASC)
