"""Spend browser time under both budgets: the run's own and the shared daily ledger (chapter 23, decision D23)."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from discovery_ingest.browser.budget import BrowserBudget
from discovery_ingest.browser.errors import BrowserAuthError, BrowserQuotaExceeded
from discovery_ingest.budget import BudgetGuard
from discovery_ingest.worker.stop import StopDrain

ESTIMATE_SECONDS = 30.0
"""Reserved before each call: the navigation timeout, the most one page can cost."""
T = TypeVar("T")


class BrowserSpend:
    """Wrap each browser call: check the run budget, reserve, call, settle; map limits to :class:`StopDrain`."""

    def __init__(self, budget: BrowserBudget, guard: BudgetGuard) -> None:
        """Pair the run ``budget`` with the ledger ``guard``."""
        self._budget = budget
        self._guard = guard

    @property
    def used_seconds(self) -> float:
        """Browser seconds this run has spent."""
        return self._budget.used_seconds

    def call(self, action: Callable[[], T], cost_ms: Callable[[T], int]) -> T:
        """Run ``action`` under the budgets; ``cost_ms`` reads its browser milliseconds from the result."""
        if self._budget.exhausted:
            raise StopDrain("browser_budget", "the run's browser budget is spent")
        reserved = self._reserve()
        result = self._run(action)
        spent = cost_ms(result)
        self._budget.spend(spent)
        if reserved:
            self._guard.adjust("browser_seconds", spent / 1000 - ESTIMATE_SECONDS)
        return result

    def _reserve(self) -> bool:
        answer = self._guard.reserve("browser_seconds", ESTIMATE_SECONDS)
        if answer.ledger_unavailable:
            return False
        if not answer.granted:
            raise StopDrain("browser_budget", "the day's browser seconds are spent")
        return True

    def _run(self, action: Callable[[], T]) -> T:
        try:
            return action()
        except BrowserQuotaExceeded as err:
            self._guard.exhaust("browser_seconds")
            raise StopDrain("browser_quota", str(err)) from err
        except BrowserAuthError as err:
            raise StopDrain("error", f"Cloudflare rejected the browser credentials: {err}") from err


def open_browser_spend(limit_seconds: float, guard: BudgetGuard) -> BrowserSpend | None:
    """Return the spend for a run, capped by what the ledger has left today; ``None`` when nothing can be spent."""
    left = guard.remaining("browser_seconds")
    if left.exhausted or (left.remaining is not None and left.remaining < ESTIMATE_SECONDS):
        return None
    limit = limit_seconds if left.remaining is None else min(limit_seconds, left.remaining)
    return BrowserSpend(BrowserBudget(limit), guard)
