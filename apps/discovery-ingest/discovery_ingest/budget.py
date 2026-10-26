"""Worker-side view of the budget ledger: a denial is normal, an unreachable ledger never raises."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar

import httpx
from pydantic import ValidationError

from discovery_ingest.api_client import DiscoveryMachineApiError, DiscoveryMachineClient
from discovery_ingest.budget_models import BudgetResource, BudgetSnapshot

LEDGER_ERRORS = (DiscoveryMachineApiError, httpx.HTTPError, ValidationError)
"""Everything that can mean "the ledger did not answer": a 5xx, a 404 from an API without the routes, a transport
failure or an unreadable body. The caller falls back to its own run budget and reports ``ledger_unavailable``."""

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class Remaining:
    """What is left of one resource; ``remaining`` is ``None`` when the ledger could not be read."""

    remaining: float | None
    exhausted: bool = False
    ledger_unavailable: bool = False


@dataclass(frozen=True, slots=True)
class Reserved:
    """The outcome of a reservation; ``granted`` is false both for a denial and an unreachable ledger."""

    granted: bool
    remaining: float | None
    ledger_unavailable: bool = False


class BudgetGuard:
    """Ask the ledger before spending and report after; fall back to the run budget when it is silent.

    ``ledger_unavailable`` turns true on the first call the ledger did not answer, so a drain can say so in its report.
    """

    def __init__(self, client: DiscoveryMachineClient) -> None:
        """Wrap ``client``."""
        self._client = client
        self.ledger_unavailable = False

    def snapshot(self) -> BudgetSnapshot | None:
        """Return every resource, or ``None`` when the ledger could not be read."""
        try:
            return self._client.get_budgets()
        except LEDGER_ERRORS:
            return self._mark_unavailable(None)

    def remaining(self, resource: BudgetResource) -> Remaining:
        """Return what is left of ``resource`` today (or this month)."""
        snapshot = self.snapshot()
        if snapshot is None:
            return Remaining(None, ledger_unavailable=True)
        row = next((row for row in snapshot.items if row.resource == resource), None)
        if row is None:
            return self._mark_unavailable(Remaining(None, ledger_unavailable=True))
        return Remaining(row.remaining, row.exhausted)

    def reserve(self, resource: BudgetResource, amount: float) -> Reserved:
        """Reserve ``amount`` of ``resource``."""
        try:
            answer = self._client.reserve_budget(resource, amount)
        except LEDGER_ERRORS:
            return self._mark_unavailable(Reserved(False, None, ledger_unavailable=True))
        return Reserved(answer.granted, answer.remaining)

    def adjust(self, resource: BudgetResource, delta: float) -> bool:
        """Record the real cost of a reservation; return whether the ledger took it."""
        try:
            self._client.adjust_budget(resource, delta)
        except LEDGER_ERRORS:
            return self._mark_unavailable(False)
        return True

    def exhaust(self, resource: BudgetResource) -> bool:
        """Tell the ledger a provider's quota is gone; return whether the ledger took it."""
        try:
            self._client.exhaust_budget(resource)
        except LEDGER_ERRORS:
            return self._mark_unavailable(False)
        return True

    def _mark_unavailable(self, result: T) -> T:
        self.ledger_unavailable = True
        return result
