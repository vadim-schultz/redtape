"""A neuron ledger behind a mock transport: the real machine client and guard talk to it, nothing touches the network."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
from discovery_ingest.budget import BudgetGuard
from discovery_ingest.client import DiscoveryIngestClient
from pydantic import SecretStr

_REAL_HTTPX_CLIENT = httpx.Client


class FakeLedger:
    """Answers the budget routes for the ``neurons`` resource from a remaining amount and records every call."""

    def __init__(self, remaining: float, *, cap: int = 9500, exhausted: bool = False, down: bool = False) -> None:
        self.remaining = remaining
        self.cap = cap
        self.exhausted = exhausted
        self.down = down
        self.calls: list[tuple[str, dict[str, float]]] = []

    def _row(self) -> dict[str, Any]:
        used = self.cap - self.remaining
        return {
            "resource": "neurons",
            "period": "2026-10-28",
            "cap": self.cap,
            "used": used,
            "remaining": self.remaining,
            "exhausted": self.exhausted,
        }

    def __call__(self, request: httpx.Request) -> httpx.Response:
        """Handle one request: ``GET /budgets``, ``reserve``, ``adjust`` or ``exhaust``."""
        if self.down:
            raise httpx.ConnectError("ledger unreachable")
        action = request.url.path.rsplit("/", 1)[-1]
        body = json.loads(request.content) if request.content else {}
        self.calls.append((action, body))
        if action == "budgets":
            return httpx.Response(200, json={"items": [self._row()]})
        if action == "reserve":
            return self._reserve(body["amount"])
        if action == "adjust":
            self.remaining -= body["delta"]
        if action == "exhaust":
            self.exhausted = True
        return httpx.Response(200, json=self._row())

    def _reserve(self, amount: float) -> httpx.Response:
        if self.exhausted or amount > self.remaining:
            return httpx.Response(409, json={"granted": False, "remaining": self.remaining})
        self.remaining -= amount
        return httpx.Response(200, json={"granted": True, "remaining": self.remaining})

    def actions(self) -> list[str]:
        """The route names called so far, in order."""
        return [action for action, _body in self.calls]


def guard_for(monkeypatch: pytest.MonkeyPatch, ledger: FakeLedger) -> BudgetGuard:
    """A real :class:`BudgetGuard` whose machine client is served by ``ledger``."""

    def factory(**kwargs: Any) -> httpx.Client:
        kwargs["transport"] = httpx.MockTransport(ledger)
        return _REAL_HTTPX_CLIENT(**kwargs)

    monkeypatch.setattr("discovery_ingest.client.http_client.httpx.Client", factory)
    return BudgetGuard(DiscoveryIngestClient("https://redtape.test", SecretStr("test-machine-key")).budget)
