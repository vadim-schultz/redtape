"""Fail and release of tasks a key holds, written once for every work-task table."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import NamedTuple
from uuid import UUID

from app.features.discovery.task_retry import FailureKind
from app.features.search.errors import TaskNotOwnedError
from app.features.search.leased_queue import LeasedQueue, TaskT
from app.features.search.task_settle import fail_task, release_task


class Released(NamedTuple):
    """The ids a release handed back and the ones the key did not hold, each in request order without repeats."""

    released: list[UUID]
    skipped: list[UUID]


def fail_owned(
    queue: LeasedQueue[TaskT], api_key_id: UUID, task_id: UUID, error: str, kind: FailureKind, now: datetime
) -> TaskT:
    """Record ``error`` on the task ``api_key_id`` holds; raise :exc:`TaskNotOwnedError` for any other task."""
    task = queue.owned(task_id, api_key_id)
    if task is None:
        raise TaskNotOwnedError()
    fail_task(task, error, kind, now)
    return task


def release_owned(queue: LeasedQueue[TaskT], api_key_id: UUID, task_ids: Sequence[UUID], reason: str) -> Released:
    """Hand back every listed task the key holds without consuming an attempt; report the rest as skipped."""
    unique_ids = list(dict.fromkeys(task_ids))
    tasks = [task for task_id in unique_ids if (task := queue.owned(task_id, api_key_id))]
    for task in tasks:
        release_task(task, reason)
    released = {task.id for task in tasks}
    return Released(
        released=[task_id for task_id in unique_ids if task_id in released],
        skipped=[task_id for task_id in unique_ids if task_id not in released],
    )
