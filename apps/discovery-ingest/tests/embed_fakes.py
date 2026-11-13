"""Fakes for the embedding drain tests: a machine API with the embedding routes and the ledger, and a scripted embedder."""

from __future__ import annotations

import json
import uuid
from collections import defaultdict
from collections.abc import Callable, Sequence
from typing import Any

import httpx
import pytest
from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.extract.embedding.client import EmbeddingResult
from pydantic import SecretStr

from ledger_fakes import FakeLedger
from run_stub import run_response

MODEL = "@cf/qwen/qwen3-embedding-0.6b"
API_BASE = "https://redtape.test"
API_KEY = "test-machine-key"
DIMENSION = 4
_REAL_HTTPX_CLIENT = httpx.Client
CLOUDFLARE_HOST = "api.cloudflare.com"
Handler = Callable[[httpx.Request], httpx.Response]


def task(number: int, text: str | None = None) -> dict[str, str]:
    """A claimed embedding task whose text is ``text-<number>`` (the scripted embedder reads the number back)."""
    return {
        "task_id": str(uuid.UUID(int=number + 1)),
        "candidate_id": str(uuid.UUID(int=1000 + number)),
        "locale": "de",
        "text": text or f"text-{number}",
        "text_hash": f"hash-{number}",
        "lease_expires_at": "2026-11-10T12:00:00Z",
    }


def task_id(number: int) -> str:
    """The id of ``task(number)``."""
    return str(uuid.UUID(int=number + 1))


def vector_of(text: str) -> tuple[float, ...]:
    """The vector the scripted embedder returns for ``text-<number>``."""
    return (float(text.rsplit("-", 1)[1]),) * DIMENSION


class EmbedApi:
    """The embedding machine routes and the neuron ledger behind one mock transport; every body is recorded per route."""

    def __init__(self, tasks: Sequence[dict[str, str]], *, ledger: FakeLedger | None = None) -> None:
        self.queue = list(tasks)
        self.ledger = ledger or FakeLedger(9000.0)
        self.outcomes: dict[str, tuple[str, str | None]] = {}
        self.forced: dict[str, tuple[int, str]] = {}
        self.unreachable: set[str] = set()
        self.bodies: dict[str, list[dict[str, Any]]] = defaultdict(list)

    def handler(self, request: httpx.Request) -> httpx.Response:
        """Serve the five embedding routes; the ledger routes go to the :class:`FakeLedger`."""
        if "/budgets" in request.url.path:
            return self.ledger(request)
        if (run := run_response(request)) is not None:
            return run
        route = request.url.path.rsplit("/", 1)[-1]
        self.bodies[route].append(json.loads(request.content) if request.content else {})
        if route in self.unreachable:
            raise httpx.ReadTimeout(f"{route} timed out")
        if route in self.forced:
            status, detail = self.forced[route]
            return httpx.Response(status, json={"detail": detail})
        return getattr(self, f"_{route}")(self.bodies[route][-1])

    def client(self) -> DiscoveryIngestClient:
        """A machine client whose transport is this API."""
        return DiscoveryIngestClient(API_BASE, SecretStr(API_KEY), transport=httpx.MockTransport(self.handler))

    def install(self, monkeypatch: pytest.MonkeyPatch, cloudflare: Handler | None = None) -> None:
        """Route every ``httpx.Client`` the code under test builds: Workers AI calls to ``cloudflare``, the rest here."""

        def route(request: httpx.Request) -> httpx.Response:
            if cloudflare is not None and request.url.host == CLOUDFLARE_HOST:
                return cloudflare(request)
            return self.handler(request)

        def factory(**kwargs: Any) -> httpx.Client:
            kwargs["transport"] = httpx.MockTransport(route)
            return _REAL_HTTPX_CLIENT(**kwargs)

        monkeypatch.setattr("discovery_ingest.client.http_client.httpx.Client", factory)

    def _claim(self, body: dict[str, Any]) -> httpx.Response:
        taken, self.queue = self.queue[: body["limit"]], self.queue[body["limit"] :]
        return httpx.Response(200, json={"items": taken})

    def _complete(self, body: dict[str, Any]) -> httpx.Response:
        results = [self._result(item["task_id"]) for item in body["items"]]
        return httpx.Response(200, json={"items": results})

    def _result(self, identifier: str) -> dict[str, Any]:
        outcome, reason = self.outcomes.get(identifier, ("stored", None))
        return {"task_id": identifier, "outcome": outcome, "reason": reason}

    def _fail(self, body: dict[str, Any]) -> httpx.Response:
        return httpx.Response(200, json={"task_id": body["task_id"], "status": "pending", "last_error": body["error"]})

    def _release(self, body: dict[str, Any]) -> httpx.Response:
        return httpx.Response(200, json={"released": body["task_ids"], "skipped": []})

    def _summary(self, _body: dict[str, Any]) -> httpx.Response:
        count = len(self.queue)
        return httpx.Response(200, json={"pending_ready": count, "claimed": 0, "failed": 0, "stale_candidates": 0})


class ScriptedEmbedder:
    """Returns or raises the next scripted outcome per call; ``None`` means a normal answer; the last one repeats."""

    def __init__(self, *outcomes: Exception | None, neurons: float | None = 0.1) -> None:
        self.outcomes = list(outcomes) or [None]
        self.neurons = neurons
        self.batches: list[list[str]] = []

    def embed(self, texts: Sequence[str], *, dimensions: int | None = None) -> EmbeddingResult:
        """Record the batch, then raise the scripted error or return one vector per text in order."""
        self.batches.append(list(texts))
        outcome = self.outcomes.pop(0) if len(self.outcomes) > 1 else self.outcomes[0]
        if outcome is not None:
            raise outcome
        vectors = tuple(vector_of(text) for text in texts)
        return EmbeddingResult(vectors, DIMENSION, MODEL, 10 * len(texts), self.neurons, 5)
