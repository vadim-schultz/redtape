"""The leased tasks of one batch that nobody has settled yet: what a stop hands back to the queue."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Generic, TypeVar
from uuid import UUID

from discovery_ingest.worker.lease_settle import HasTaskId

TaskT = TypeVar("TaskT", bound=HasTaskId)


class OpenTasks(Generic[TaskT]):
    """Track which claimed tasks are still leased to this key as the batch settles them."""

    def __init__(self, tasks: Iterable[TaskT]) -> None:
        """Start with every claimed task open."""
        self._tasks = list(tasks)

    def settled(self, task_ids: Iterable[UUID]) -> None:
        """Forget the tasks the API has settled or handed back."""
        done = set(task_ids)
        self._tasks = [task for task in self._tasks if task.task_id not in done]

    def remaining(self) -> list[TaskT]:
        """Return the tasks that are still leased to this key, in claim order."""
        return list(self._tasks)

    def among(self, group: Iterable[TaskT]) -> list[TaskT]:
        """Return the tasks of ``group`` that are still open."""
        ids = {task.task_id for task in group}
        return [task for task in self._tasks if task.task_id in ids]
