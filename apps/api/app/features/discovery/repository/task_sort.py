"""Orderings of the admin task listing: a public sort key plus a direction, always tied to the queue order."""

from __future__ import annotations

import enum
from collections.abc import Mapping

from sqlalchemy import ColumnElement, String, cast

from app.features.discovery.repository.tasks import QUEUE_ORDER
from app.models.discovery import CatalogueService, DiscoveryTask
from app.shared.list_query import SortOrder

Ordering = tuple[ColumnElement, ...]


class TaskSortKey(enum.StrEnum):
    """Public sort fields of the task list."""

    TARGET = "target"
    KIND = "kind"
    STATUS = "status"
    SOURCE = "source"
    PRIORITY = "priority"
    ATTEMPTS = "attempts"


_PRIMARY: Mapping[TaskSortKey, ColumnElement] = {
    TaskSortKey.TARGET: DiscoveryTask.target_url.expression,
    TaskSortKey.KIND: cast(DiscoveryTask.kind, String),
    TaskSortKey.STATUS: cast(DiscoveryTask.status, String),
    TaskSortKey.SOURCE: cast(CatalogueService.source, String),
    TaskSortKey.PRIORITY: DiscoveryTask.priority.expression,
    TaskSortKey.ATTEMPTS: DiscoveryTask.attempt_count.expression,
}


def task_ordering(key: TaskSortKey | None, order: SortOrder) -> Ordering:
    """Return the requested key and direction followed by the queue order; the queue order alone without a key."""
    if key is None:
        return QUEUE_ORDER
    primary = _PRIMARY[key]
    return (primary.desc() if order is SortOrder.DESC else primary.asc(), *QUEUE_ORDER)
