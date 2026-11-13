"""A budget ledger behind a mock transport: the real machine client and guard talk to it, nothing touches the network.

The ``neurons`` row is the daily ledger every test starts from. ``characters`` adds the monthly ``azure_translator_chars``
row, which answers reserve, adjust and exhaust the way the API does. Every reserve, adjust and exhaust is kept in ``writes``.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest
from discovery_ingest.budget import BudgetGuard
from discovery_ingest.client import DiscoveryIngestClient
from pydantic import SecretStr

_REAL_HTTPX_CLIENT = httpx.Client
CHARACTERS = "azure_translator_chars"
CHARACTERS_CAP = 1_900_000
Handler = Callable[[httpx.Request], httpx.Response]


class _Characters:
    """The monthly character row: a reserve is all or nothing, an adjust is signed, an exhaust closes the period."""

    def __init__(self, remaining: float) -> None:
        self.remaining = remaining
        self.exhausted = False

    def row(self) -> dict[str, Any]:
        """The row as ``GET /budgets`` reports it."""
        return {
            "resource": CHARACTERS,
            "period": "2026-11",
            "cap": CHARACTERS_CAP,
            "used": CHARACTERS_CAP - self.remaining,
            "remaining": self.remaining,
            "exhausted": self.exhausted,
        }

    def answer(self, action: str, body: dict[str, Any]) -> httpx.Response:
        """Answer one reserve, adjust or exhaust; a refused reserve is a 409 with ``granted`` false."""
        if action == "reserve":
            return self._reserve(body["amount"])
        if action == "adjust":
            self.remaining -= body["delta"]
        if action == "exhaust":
            self.exhausted = True
        return httpx.Response(200, json=self.row())

    def _reserve(self, amount: float) -> httpx.Response:
        if self.exhausted or amount > self.remaining:
            return httpx.Response(409, json={"granted": False, "remaining": self.remaining})
        self.remaining -= amount
        return httpx.Response(200, json={"granted": True, "remaining": self.remaining})


class FakeLedger:
    """Answers the budget routes for ``neurons`` (and ``azure_translator_chars`` when ``characters`` is given)."""

    def __init__(
        self,
        remaining: float,
        *,
        cap: int = 9500,
        exhausted: bool = False,
        down: bool = False,
        characters: float | None = None,
    ) -> None:
        self.remaining = remaining
        self.cap = cap
        self.exhausted = exhausted
        self.down = down
        self.characters = None if characters is None else _Characters(characters)
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.writes: list[tuple[str, str]] = []

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

    def _rows(self) -> list[dict[str, Any]]:
        return [self._row()] if self.characters is None else [self._row(), self.characters.row()]

    def __call__(self, request: httpx.Request) -> httpx.Response:
        """Handle one request: ``GET /budgets``, then ``reserve``, ``adjust`` or ``exhaust`` on a resource."""
        if self.down:
            raise httpx.ConnectError("ledger unreachable")
        action = request.url.path.rsplit("/", 1)[-1]
        body = json.loads(request.content) if request.content else {}
        self.calls.append((action, body))
        if action == "budgets":
            return httpx.Response(200, json={"items": self._rows()})
        resource = request.url.path.rsplit("/", 2)[-2]
        self.writes.append((resource, action))
        if resource == CHARACTERS:
            return self._characters_answer(action, body)
        if action == "reserve":
            return self._reserve(body["amount"])
        if action == "adjust":
            self.remaining -= body["delta"]
        if action == "exhaust":
            self.exhausted = True
        return httpx.Response(200, json=self._row())

    def _characters_answer(self, action: str, body: dict[str, Any]) -> httpx.Response:
        if self.characters is None:
            return httpx.Response(404, json={"detail": "Unknown budget resource"})
        return self.characters.answer(action, body)

    def _reserve(self, amount: float) -> httpx.Response:
        if self.exhausted or amount > self.remaining:
            return httpx.Response(409, json={"granted": False, "remaining": self.remaining})
        self.remaining -= amount
        return httpx.Response(200, json={"granted": True, "remaining": self.remaining})

    def actions(self) -> list[str]:
        """The route names called so far, in order."""
        return [action for action, _body in self.calls]

    def writes_to(self, resource: str) -> list[str]:
        """The reserve, adjust and exhaust calls sent for ``resource``, in order."""
        return [action for name, action in self.writes if name == resource]


def guard_for(monkeypatch: pytest.MonkeyPatch, ledger: Handler) -> BudgetGuard:
    """A real :class:`BudgetGuard` whose machine client is served by ``ledger``."""

    def factory(**kwargs: Any) -> httpx.Client:
        kwargs["transport"] = httpx.MockTransport(ledger)
        return _REAL_HTTPX_CLIENT(**kwargs)

    monkeypatch.setattr("discovery_ingest.client.http_client.httpx.Client", factory)
    return BudgetGuard(DiscoveryIngestClient("https://redtape.test", SecretStr("test-machine-key")).budget)
