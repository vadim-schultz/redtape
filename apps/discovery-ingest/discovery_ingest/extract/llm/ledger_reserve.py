"""Reserve neurons from the ledger, asking once more for what is left when the full amount does not fit."""

from __future__ import annotations

from dataclasses import dataclass

from discovery_ingest.budget import BudgetGuard
from discovery_ingest.budget_models import BudgetResource


@dataclass(frozen=True, slots=True)
class LedgerGrant:
    """What the ledger granted: ``amount`` is 0 when it refused or did not answer (``ledger_unavailable``)."""

    amount: float
    ledger_unavailable: bool = False


def reserve_up_to(guard: BudgetGuard, resource: BudgetResource, amount: float) -> LedgerGrant:
    """Reserve ``amount``; when the ledger denies it with neurons left, reserve exactly what is left, once."""
    first = guard.reserve(resource, amount)
    if first.granted:
        return LedgerGrant(amount)
    if first.ledger_unavailable:
        return LedgerGrant(0.0, ledger_unavailable=True)
    return _reserve_remaining(guard, resource, first.remaining)


def _reserve_remaining(guard: BudgetGuard, resource: BudgetResource, remaining: float | None) -> LedgerGrant:
    if remaining is None or remaining <= 0:
        return LedgerGrant(0.0)
    second = guard.reserve(resource, remaining)
    return LedgerGrant(remaining if second.granted else 0.0, second.ledger_unavailable)
