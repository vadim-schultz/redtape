"""The query-embedder port: turn a normalised query into one vector, or ``None`` when that is not possible."""

from __future__ import annotations

from typing import Final, Protocol

from app.features.search.query import NormalisedQuery

QueryVector = tuple[float, ...]
"""One query embedding, as wide as the stored document vectors."""

QUERY_TASK: Final = "Given a search query for a German administrative document, retrieve the matching document"
"""The instruction the Qwen3 embedding model expects in front of a query; documents are embedded without it."""


class QueryEmbedder(Protocol):
    """Embed one query. Every failure (timeout, error, no credentials, no budget) is ``None``, never an exception."""

    def embed(self, query: NormalisedQuery) -> QueryVector | None:
        """Return the vector of ``query``, or ``None`` when it cannot be embedded right now."""
        ...


class UnavailableQueryEmbedder:
    """The embedder of a deployment without Workers AI credentials: search stays keyword-only."""

    def embed(self, query: NormalisedQuery) -> QueryVector | None:  # noqa: ARG002
        """Return ``None``: nothing can be embedded."""
        return None


def instructed(query: NormalisedQuery) -> str:
    """Return the text the model embeds for ``query``: the instruction, then the query."""
    return f"Instruct: {QUERY_TASK}\nQuery: {query.text}"
