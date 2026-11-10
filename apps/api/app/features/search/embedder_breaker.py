"""A circuit breaker in front of the query embedder: a failing provider is skipped for a cooldown, not waited on."""

from __future__ import annotations

import time
from collections.abc import Callable
from threading import Lock

from app.features.search.query import NormalisedQuery
from app.features.search.query_embedder import QueryEmbedder, QueryVector


class CircuitBreakerQueryEmbedder:
    """Stop calling the wrapped embedder after ``failures`` misses in a row, and answer ``None`` at once.

    After ``cooldown_s`` one probe call goes through; a success closes the breaker, a miss keeps it open for another
    cooldown. Every ``None`` counts as a miss, a refused neuron budget included, which also spares the ledger a write
    per search while the budget is gone.
    """

    def __init__(
        self,
        inner: QueryEmbedder,
        *,
        failures: int,
        cooldown_s: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Wrap ``inner``; ``failures`` misses open the breaker for ``cooldown_s`` seconds of ``clock``."""
        self._inner = inner
        self._threshold = failures
        self._cooldown = cooldown_s
        self._clock = clock
        self._misses = 0
        self._retry_at = 0.0
        self._lock = Lock()

    def embed(self, query: NormalisedQuery) -> QueryVector | None:
        """Return the vector of ``query``, or ``None`` without calling the provider while the breaker is open."""
        if self._open():
            return None
        vector = self._inner.embed(query)
        self._record(hit=vector is not None)
        return vector

    def _open(self) -> bool:
        """Whether the call must be skipped; the first call after the cooldown is the probe and re-arms the wait."""
        with self._lock:
            if self._misses < self._threshold:
                return False
            if self._clock() < self._retry_at:
                return True
            self._retry_at = self._clock() + self._cooldown
            return False

    def _record(self, *, hit: bool) -> None:
        with self._lock:
            self._misses = 0 if hit else self._misses + 1
            if self._misses >= self._threshold:
                self._retry_at = self._clock() + self._cooldown
