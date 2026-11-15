"""What every leased-task drain does the same way: turn API refusals into stops, fail tasks, hand tasks back."""

from __future__ import annotations

import sys
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

import httpx

from discovery_ingest.client import DiscoveryMachineApiError
from discovery_ingest.translation.errors import RateLimited
from discovery_ingest.worker.release import MAX_REASON
from discovery_ingest.worker.stop import StopDrain
from discovery_ingest.worker.tally import FAILED

HTTP_CONFLICT = 409
SKIPPED = "skipped"


class HasTaskId(Protocol):
    """A leased task of a queue that settles by task id (an embedding task, a translation task)."""

    @property
    def task_id(self) -> UUID:
        """The id the settle routes take."""
        ...


class Released(Protocol):
    """The answer of a release call: the tasks that went back to the queue."""

    @property
    def released(self) -> list[UUID]:
        """The ids this key held and handed back."""
        ...


class LeasedTaskApi(Protocol):
    """The two settle routes every leased queue shares."""

    def fail(self, task_id: UUID, *, error: str, retryable: bool = False) -> object:
        """Fail a claimed task (409: not held by this key)."""
        ...

    def release(self, task_ids: Sequence[UUID], reason: str) -> Released:
        """Hand claimed tasks back without consuming an attempt."""
        ...


@dataclass(frozen=True, slots=True)
class Failure:
    """Why a batch could not be processed and whether the API should retry its tasks."""

    message: str
    retryable: bool


def _api_stop(err: DiscoveryMachineApiError) -> StopDrain:
    if err.is_database_limit:
        return StopDrain("db_limit", err.detail)
    return StopDrain("error", str(err))


@contextmanager
def refusals_as_stops() -> Iterator[None]:
    """Turn a machine API call that failed into the stop that ends the drain.

    The soft limit is ``db_limit``; any other refusal and any transport failure (the outcome of the call is unknown)
    is ``error``, so the batch in hand is released and the report is still printed.
    """
    try:
        yield
    except DiscoveryMachineApiError as err:
        raise _api_stop(err) from err
    except httpx.HTTPError as err:
        raise StopDrain("error", f"{type(err).__name__}: {err}") from err


def fail_batch(api: LeasedTaskApi, tasks: Sequence[HasTaskId], failure: Failure) -> list[str]:
    """Fail every task of a batch that could not be processed; return one outcome label per task."""
    return [_fail_one(api, task, failure) for task in tasks]


def _fail_one(api: LeasedTaskApi, task: HasTaskId, failure: Failure) -> str:
    try:
        api.fail(task.task_id, error=failure.message, retryable=failure.retryable)
    except DiscoveryMachineApiError as err:
        if err.status_code != HTTP_CONFLICT:
            raise
        print(f"fail of task {task.task_id} refused: {err}", file=sys.stderr)
        return SKIPPED
    return FAILED


def limit_stop(err: RateLimited) -> StopDrain:
    """Return the stop a throttled batch ends with: ``rate_limited``, so the batch's open tasks go back without an attempt.

    Both settle modules raise it; the drain's batch step then releases what nobody settled, and no further claim runs.
    """
    return StopDrain("rate_limited", str(err))


def release_batch(api: LeasedTaskApi, tasks: Sequence[HasTaskId], reason: str) -> int:
    """Hand tasks back without consuming an attempt; return how many the API took (a failure is logged, never raised)."""
    if not tasks:
        return 0
    try:
        answer = api.release([task.task_id for task in tasks], reason[:MAX_REASON])
    except (DiscoveryMachineApiError, httpx.HTTPError) as err:
        print(f"release of {len(tasks)} tasks failed: {err}", file=sys.stderr)
        return 0
    return len(answer.released)
