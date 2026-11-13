"""Fakes for the translate drain tests: a machine API with the translation routes and the ledger, and a scripted engine."""

from __future__ import annotations

import json
import uuid
from collections import defaultdict
from collections.abc import Callable, Sequence
from typing import Any

import httpx
import pytest
from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.translation.errors import TranslationEngineError
from discovery_ingest.translation.units import (
    CallLimits,
    TranslationBatch,
    TranslationOutcome,
    TranslationUnit,
    Usage,
    UsageUnit,
)
from pydantic import SecretStr

from ledger_fakes import FakeLedger

API_BASE = "https://redtape.test"
API_KEY = "test-machine-key"
ENGINE_NAME = "scripted"
MODEL = "scripted-model-1"
_REAL_HTTPX_CLIENT = httpx.Client
CLOUDFLARE_HOST = "api.cloudflare.com"
AZURE_HOST = "api.cognitive.microsofttranslator.com"
Handler = Callable[[httpx.Request], httpx.Response]


def task_id(number: int) -> str:
    """The id of ``task(number)``."""
    return str(uuid.UUID(int=number + 1))


def task(number: int, locale: str = "en") -> dict[str, str]:
    """A claimed translation task; its German title and description carry the number so a translation keeps them."""
    return {
        "task_id": task_id(number),
        "candidate_id": str(uuid.UUID(int=1000 + number)),
        "locale": locale,
        "source_locale": "de",
        "title": f"Reisepass beantragen {number}",
        "description": f"Der Reisepass kostet 60 Euro, Fall {number}.",
        "source_hash": f"hash-{number}",
        "lease_expires_at": "2026-11-10T12:00:00Z",
    }


class TranslateApi:
    """The translation machine routes and the neuron ledger behind one mock transport; every body is recorded per route."""

    def __init__(self, tasks: Sequence[dict[str, str]], *, ledger: FakeLedger | None = None) -> None:
        self.queue = list(tasks)
        self.ledger = ledger or FakeLedger(9000.0)
        self.outcomes: dict[str, tuple[str, str | None]] = {}
        self.forced: dict[str, tuple[int, str]] = {}
        self.unreachable: set[str] = set()
        self.bodies: dict[str, list[dict[str, Any]]] = defaultdict(list)

    def handler(self, request: httpx.Request) -> httpx.Response:
        """Serve the five translation routes; the ledger routes go to the :class:`FakeLedger`."""
        if "/budgets" in request.url.path:
            return self.ledger(request)
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

    def install(
        self, monkeypatch: pytest.MonkeyPatch, cloudflare: Handler | None = None, azure: Handler | None = None
    ) -> None:
        """Route every ``httpx.Client`` the code under test builds: Workers AI calls to ``cloudflare``, Azure to ``azure``, the rest here."""

        def route(request: httpx.Request) -> httpx.Response:
            if cloudflare is not None and request.url.host == CLOUDFLARE_HOST:
                return cloudflare(request)
            if azure is not None and request.url.host == AZURE_HOST:
                return azure(request)
            return self.handler(request)

        def factory(**kwargs: Any) -> httpx.Client:
            kwargs["transport"] = httpx.MockTransport(route)
            return _REAL_HTTPX_CLIENT(**kwargs)

        monkeypatch.setattr("discovery_ingest.client.http_client.httpx.Client", factory)

    def posted(self) -> list[dict[str, Any]]:
        """Every item posted to ``complete``, in order."""
        return [item for body in self.bodies["complete"] for item in body["items"]]

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
        row = {"locale": "en", "pending_ready": count, "claimed": 0, "failed": 0, "stale": 0, "translated": 0}
        return httpx.Response(200, json={"locales": [row, {**row, "locale": "tr", "pending_ready": 0}]})


def _drop_digits(text: str) -> str:
    return "".join(char for char in text if not char.isdigit())


class ScriptedEngine:
    """A translation engine for tests: prefixes every text with its locale, so numbers survive; failures are scripted.

    ``broken`` keys lose their numbers in the first translation and are right after a repair; ``stubborn`` keys lose
    them every time. ``outcomes`` are raised or served per call (``None`` is a normal answer; the last one repeats).
    """

    name = ENGINE_NAME
    repairs = True

    def __init__(
        self,
        *outcomes: TranslationEngineError | None,
        unit: UsageUnit = "neurons",
        neurons: float = 2.0,
        broken: Sequence[int] = (),
        stubborn: Sequence[int] = (),
        short: bool = False,
    ) -> None:
        self.usage_unit: UsageUnit = unit
        self.outcomes = list(outcomes) or [None]
        self.neurons = neurons
        self.broken = {task_id(number) for number in broken}
        self.stubborn = {task_id(number) for number in stubborn}
        self.short = short
        self.batches: list[TranslationBatch] = []

    def translate(self, batch: TranslationBatch) -> TranslationOutcome:
        """Record the batch, then raise the scripted error or return one translated unit per unit in order."""
        self.batches.append(batch)
        outcome = self.outcomes.pop(0) if len(self.outcomes) > 1 else self.outcomes[0]
        if outcome is not None:
            raise outcome
        units = batch.units[:-1] if self.short else batch.units
        repairing = {correction.key for correction in batch.corrections}
        results = tuple(self._render(batch, unit, unit.key in repairing) for unit in units)
        return TranslationOutcome(results, Usage(self.usage_unit, self.neurons * len(units)), MODEL)

    @property
    def limits(self) -> CallLimits:
        """One call of up to 50 units at a time, as the Workers AI adapter has it."""
        return CallLimits(units_per_call=50, concurrency=1)

    def estimate(self, batch: TranslationBatch) -> Usage:
        """Reserve the cost of the units plus one."""
        return Usage(self.usage_unit, self.neurons * (len(batch.units) + 1))

    def _render(self, batch: TranslationBatch, unit: TranslationUnit, repairing: bool) -> TranslationUnit:
        lose = unit.key in self.stubborn or (unit.key in self.broken and not repairing)
        text = _drop_digits if lose else str
        return TranslationUnit(
            unit.key, f"[{batch.target_locale}] {text(unit.title)}", f"[{batch.target_locale}] {text(unit.description)}"
        )
