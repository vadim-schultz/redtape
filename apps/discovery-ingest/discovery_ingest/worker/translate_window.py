"""The concurrency window of a translate batch: at most N engine calls in flight, each settled in call order.

A call starts only once an earlier one has settled. So a stop raised while settling (a quota, a refused post) holds back
every call that has not started yet, exactly as a sequential drain would.
"""

from __future__ import annotations

import threading
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from itertools import islice

from discovery_ingest.translation.errors import TranslationEngineError
from discovery_ingest.translation.repair import Translator
from discovery_ingest.worker.stop import StopDrain
from discovery_ingest.worker.translate_group import (
    CallResult,
    Tasks,
    batch_of,
    settle_call,
    settle_failed_call,
    translate_call,
)
from discovery_ingest.worker.translate_settle import BatchState

Answer = CallResult | TranslationEngineError | StopDrain | None
"""A call's outcome: its result, the error it failed with, the stop that ended the drain, or ``None`` when a stop was
already raised and the call never started (its tasks are released with the rest of the batch)."""


def _answer(translator: Translator, group: Tasks, halt: threading.Event) -> Answer:
    """Translate one call unless a stop was raised; an error or a stop is returned, not raised, so the others settle."""
    if halt.is_set():
        return None
    try:
        return translate_call(translator, batch_of(group))
    except TranslationEngineError as err:
        return err
    except StopDrain as stop:
        halt.set()
        return stop


@dataclass(slots=True)
class Window:
    """The calls of one batch on a pool of at most ``size`` threads, sharing one translator and one stop flag."""

    translator: Translator
    pool: ThreadPoolExecutor
    size: int
    halt: threading.Event = field(init=False, default_factory=threading.Event)

    def start(self, group: Tasks) -> tuple[Tasks, Future[Answer]]:
        """Start the translation of one call on the pool."""
        return group, self.pool.submit(_answer, self.translator, group, self.halt)


def _settle_answer(state: BatchState, group: Tasks, answer: Answer) -> None:
    if isinstance(answer, CallResult):
        settle_call(state, group, answer)
    elif isinstance(answer, TranslationEngineError):
        settle_failed_call(state, group, answer)
    elif isinstance(answer, StopDrain):
        raise answer


def settle_window(window: Window, calls: list[Tasks], state: BatchState) -> None:
    """Settle ``calls`` in order, keeping at most ``window.size`` of them in flight.

    The first call is started at once; each later call starts when the settling of an earlier one has finished.
    """
    upcoming = iter(calls)
    queued = deque(window.start(group) for group in islice(upcoming, window.size))
    while queued:
        group, future = queued.popleft()
        _settle_answer(state, group, future.result())
        queued.extend(window.start(nxt) for nxt in islice(upcoming, 1))
