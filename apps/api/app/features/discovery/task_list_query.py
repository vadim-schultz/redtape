"""Canonical list-query allowlist of the admin task listing and its mapping to a ``TaskFilter``."""

from __future__ import annotations

from dataclasses import replace

from litestar.params import Parameter

from app.features.discovery.list_query import DiscoveryListQuery
from app.features.discovery.repository import Page, TaskFilter, TaskSortKey
from app.models.discovery import DiscoverySource, DiscoveryTaskKind, DiscoveryTaskStatus
from app.shared.list_query import ListQuery, ListQuerySpec, SortOrder, enum_filter
from app.shared.paging import PageParams

TASK_LIST_SPEC = ListQuerySpec(
    sort_keys=frozenset(key.value for key in TaskSortKey),
    filters={
        "status": enum_filter(DiscoveryTaskStatus),
        "source": enum_filter(DiscoverySource),
        "kind": enum_filter(DiscoveryTaskKind),
    },
)


def provide_task_query(
    page: PageParams,
    list_query: ListQuery,
    status: DiscoveryTaskStatus | None = Parameter(query="status", default=None),
    source: DiscoverySource | None = Parameter(query="source", default=None),
    kind: DiscoveryTaskKind | None = Parameter(query="kind", default=None),
) -> DiscoveryListQuery[TaskFilter]:
    """Collect the task list parameters, legacy and canonical, into one filter and page."""
    task_filter = task_filter_from(list_query, TaskFilter(status=status, source=source, kind=kind))
    return DiscoveryListQuery(filters=task_filter, page=Page(offset=page.offset, limit=page.limit))


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
