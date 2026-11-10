"""An in-process LRU cache in front of a query embedder, keyed by model and normalised query."""

from __future__ import annotations

from collections import OrderedDict
from threading import Lock

from app.features.search.query import NormalisedQuery
from app.features.search.query_embedder import QueryEmbedder, QueryVector


class CachedQueryEmbedder:
    """Remember the vector of each distinct query; failures are never remembered, ``size`` 0 disables the cache."""

    def __init__(self, inner: QueryEmbedder, model: str, *, size: int) -> None:
        """Wrap ``inner`` for ``model`` with room for ``size`` entries."""
        self._inner = inner
        self._model = model
        self._size = size
        self._entries: OrderedDict[tuple[str, str], QueryVector] = OrderedDict()
        self._lock = Lock()

    def embed(self, query: NormalisedQuery) -> QueryVector | None:
        """Return the cached vector of ``query``, else embed it with the wrapped embedder and remember the result."""
        key = (self._model, query.text)
        cached = self._recall(key)
        if cached is not None:
            return cached
        vector = self._inner.embed(query)
        if vector is not None:
            self._remember(key, vector)
        return vector

    def _recall(self, key: tuple[str, str]) -> QueryVector | None:
        with self._lock:
            vector = self._entries.get(key)
            if vector is not None:
                self._entries.move_to_end(key)
            return vector

    def _remember(self, key: tuple[str, str], vector: QueryVector) -> None:
        if self._size == 0:
            return
        with self._lock:
            self._entries[key] = vector
            while len(self._entries) > self._size:
                self._entries.popitem(last=False)
