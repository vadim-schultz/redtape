"""Canonical list-query allowlist of the admin task listing and its mapping to a ``TaskFilter``."""

from __future__ import annotations

from dataclasses import replace

from app.features.discovery.repository import TaskFilter, TaskSortKey
from app.models.discovery import DiscoverySource, DiscoveryTaskKind, DiscoveryTaskStatus
from app.shared.list_query import ListQuery, ListQuerySpec, SortOrder, enum_filter

TASK_LIST_SPEC = ListQuerySpec(
    sort_keys=frozenset(key.value for key in TaskSortKey),
    filters={
        "status": enum_filter(DiscoveryTaskStatus),
        "source": enum_filter(DiscoverySource),
        "kind": enum_filter(DiscoveryTaskKind),
    },
)


def task_filter_from(query: ListQuery, legacy: TaskFilter) -> TaskFilter:
    """Return the filter for ``query``; canonical parameters win over the ``legacy`` ones they replace."""
    narrowed = replace(
        legacy,
        q=query.q,
        status=query.filter_or("status", DiscoveryTaskStatus, legacy.status),
        source=query.filter_or("source", DiscoverySource, legacy.source),
        kind=query.filter_or("kind", DiscoveryTaskKind, legacy.kind),
    )
    if query.sort_by is None:
        return narrowed
    return replace(narrowed, sort_by=TaskSortKey(query.sort_by), sort_order=query.sort_order or SortOrder.ASC)
