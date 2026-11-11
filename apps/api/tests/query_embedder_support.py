"""Fakes shared by the query-embedder and search tests: an in-memory embedder and a scripted Workers AI transport."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

import httpx
from app.features.search.query import NormalisedQuery
from app.features.search.query_embedder import QueryVector

ACCOUNT = "acct-123"
TOKEN = "tok-secret-456"


@dataclass(slots=True)
class FakeQueryEmbedder:
    """Return a fixed vector per normalised query text (``None`` for an unknown text) and remember every call."""

    vectors: Mapping[str, QueryVector] = field(default_factory=dict)
    calls: list[str] = field(default_factory=list)

    def embed(self, query: NormalisedQuery) -> QueryVector | None:
        """Return the scripted vector of ``query``, or ``None``."""
        self.calls.append(query.text)
        return self.vectors.get(query.text)


def answer(vector: list[float]) -> httpx.Response:
    """Return the 200 body Workers AI answers an embedding call with."""
    return httpx.Response(200, json={"success": True, "result": {"data": [vector], "usage": {"prompt_tokens": 9}}})


@dataclass(slots=True)
class ScriptedWorkersAi:
    """An ``httpx`` client whose transport answers with ``respond`` and records the requests it saw."""

    respond: Callable[[httpx.Request], httpx.Response]
    requests: list[httpx.Request] = field(default_factory=list)

    def client(self) -> httpx.Client:
        """Return a client wired to this script."""

        def handler(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            return self.respond(request)

        return httpx.Client(transport=httpx.MockTransport(handler))

    def sent_text(self) -> str:
        """Return the one text of the first recorded request body."""
        return json.loads(self.requests[0].content)["text"][0]
