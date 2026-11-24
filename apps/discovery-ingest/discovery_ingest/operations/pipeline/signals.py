"""The stage processes that are running, and the stop that SIGTERM or SIGINT turns into for all of them."""

from __future__ import annotations

import signal
import threading
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from types import FrameType

from discovery_ingest.operations.pipeline.process import StageProcess


class StageRegistry:
    """The stage processes that are running and whether a stop signal has arrived.

    A stop is forwarded to every process running at the time and to any process admitted after it.
    """

    def __init__(self) -> None:
        """Start with no process running and no stop."""
        self._lock = threading.Lock()
        self._live: set[StageProcess] = set()
        self._signum: int | None = None

    @property
    def stopping(self) -> bool:
        """Return whether a stop signal has arrived."""
        return self._signum is not None

    def admit(self, process: StageProcess) -> None:
        """Count ``process`` as running; if a stop has already arrived, forward it to the process at once."""
        with self._lock:
            if self._signum is not None:
                process.send_signal(self._signum)
            self._live.add(process)

    def release(self, process: StageProcess) -> None:
        """Stop counting ``process`` as running."""
        with self._lock:
            self._live.discard(process)

    def stop(self, signum: int) -> None:
        """Record the stop and forward ``signum`` to every running process."""
        with self._lock:
            self._signum = signum
            for process in self._live:
                process.send_signal(signum)

    @contextmanager
    def handlers(self) -> Iterator[None]:
        """Forward SIGTERM and SIGINT to the stages for the length of the block; off the main thread, nothing is installed."""
        if threading.current_thread() is not threading.main_thread():
            yield
            return
        previous = {signum: signal.signal(signum, self._on_signal) for signum in (signal.SIGTERM, signal.SIGINT)}
        try:
            yield
        finally:
            _restore(previous)

    def _on_signal(self, signum: int, _frame: FrameType | None) -> None:
        """Forward the signal the process received."""
        self.stop(signum)


def _restore(previous: Mapping[signal.Signals, signal._HANDLER]) -> None:
    """Put back the handlers that were installed before :meth:`StageRegistry.handlers`, where Python knows them."""
    for signum, handler in previous.items():
        if handler is not None:
            signal.signal(signum, handler)
