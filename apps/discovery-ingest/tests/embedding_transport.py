"""A Workers AI embedding client wired to a mock transport, shared by the client and probe tests."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence

import httpx
from discovery_ingest.browser.throttle import Throttle
from discovery_ingest.extract.embedding.client import CloudflareEmbeddingClient

from llm_transport import ACCOUNT_ID, TOKEN, failure, settings

__all__ = [
    "ACCOUNT_ID",
    "EMBED_MODEL",
    "TOKEN",
    "embedding_client",
    "embedding_success",
    "failure",
    "texts_of",
    "vectors",
]

EMBED_MODEL = "@cf/qwen/qwen3-embedding-0.6b"
Handler = Callable[[httpx.Request], httpx.Response]


def vectors(count: int, dimension: int) -> list[list[float]]:
    """``count`` distinct vectors of ``dimension`` numbers."""
    return [[float(row + 1)] * dimension for row in range(count)]


def embedding_success(data: Sequence[Sequence[float]], usage: Mapping[str, float] | None = None) -> httpx.Response:
    """A native ``/ai/run`` embedding answer: ``result.data`` and, when given, ``result.usage``."""
    result: dict[str, object] = {"shape": [len(data), len(data[0]) if data else 0], "data": data}
    if usage is not None:
        result["usage"] = usage
    return httpx.Response(200, json={"result": result, "success": True, "errors": [], "messages": []})


def texts_of(request: httpx.Request) -> list[str]:
    """The ``text`` list the request carried."""
    return list(json.loads(request.content)["text"])


def embedding_client(handler: Handler, *, model: str | None = EMBED_MODEL) -> CloudflareEmbeddingClient:
    """A client whose HTTP is ``handler`` and whose throttle never really sleeps."""
    throttle = Throttle(1.0, clock=lambda: 0.0, sleep=lambda _seconds: None)
    http = httpx.Client(transport=httpx.MockTransport(handler))
    return CloudflareEmbeddingClient(settings(), model=model, http=http, throttle=throttle)
