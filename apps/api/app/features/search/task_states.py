"""The one table of legal status moves of a leased work task."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final, Protocol

from sqlalchemy import text

from app.features.search.errors import InvalidTaskMoveError
from app.models.search import WorkTaskStatus

TRANSITIONS: Final[Mapping[WorkTaskStatus, frozenset[WorkTaskStatus]]] = {
    WorkTaskStatus.PENDING: frozenset({WorkTaskStatus.CLAIMED}),
    WorkTaskStatus.CLAIMED: frozenset({WorkTaskStatus.PENDING, WorkTaskStatus.COMPLETED, WorkTaskStatus.FAILED}),
    WorkTaskStatus.COMPLETED: frozenset(),
    WorkTaskStatus.FAILED: frozenset(),
}
"""``claimed`` leaves by completion, failure, release, retry or lease expiry; ``completed`` and ``failed`` are final."""
OPEN_TASK_PREDICATE: Final = text("status in ('pending', 'claimed')")
"""The predicate of every partial unique index on open tasks; ``ON CONFLICT`` must repeat it to infer the index."""


class HasStatus(Protocol):
    """A row with a work-task status."""

    status: WorkTaskStatus


def can_move(source: WorkTaskStatus, target: WorkTaskStatus) -> bool:
    """Return whether a task may go from ``source`` to ``target``."""
    return target in TRANSITIONS[source]


def move(task: HasStatus, target: WorkTaskStatus) -> None:
    """Set the status of ``task`` to ``target``; raise :exc:`InvalidTaskMoveError` when the table forbids the move."""
    if not can_move(task.status, target):
        raise InvalidTaskMoveError(f"{task.status.value} -> {target.value}")
    task.status = target
