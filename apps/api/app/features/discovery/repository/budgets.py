"""Budget ledger persistence: atomic upserts keyed by period and resource."""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import and_, func, select, tuple_
from sqlalchemy.dialects.postgresql import Insert, insert

from app.features.discovery.repository.base import SessionRepository
from app.models.discovery import DiscoveryBudgetLedger

Ledger = DiscoveryBudgetLedger


@dataclass(frozen=True, slots=True)
class LedgerKey:
    """One counter: a resource in one UTC day or month."""

    period: str
    resource: str


@dataclass(frozen=True, slots=True)
class LedgerState:
    """What a counter holds right now."""

    used: Decimal
    exhausted: bool


class BudgetRepository(SessionRepository):
    """Read and write ``discovery_budget_ledger`` rows without read-modify-write races."""

    def _upsert(self, key: LedgerKey, *, used: Decimal, exhausted: bool = False) -> Insert:
        values = {"period": key.period, "resource": key.resource, "used": used, "exhausted": exhausted}
        return insert(Ledger).values(**values)

    def reserve_ledger(self, key: LedgerKey, amount: Decimal, cap: int) -> bool:
        """Add ``amount`` when the total stays within ``cap`` and the period is not exhausted; return whether it did.

        The caller rejects ``amount > cap`` first: the insert branch of the upsert does not evaluate the guard.
        """
        grant_if = and_(Ledger.used + amount <= cap, Ledger.exhausted.is_(False))
        stmt = (
            self._upsert(key, used=amount)
            .on_conflict_do_update(
                constraint="uq_discovery_budget_ledger_period_resource",
                set_={"used": Ledger.used + amount, "updated_at": func.now()},
                where=grant_if,
            )
            .returning(Ledger.used)
        )
        return self._session.execute(stmt).first() is not None

    def adjust_ledger(self, key: LedgerKey, delta: Decimal) -> None:
        """Apply a signed correction, never taking the counter below zero."""
        stmt = self._upsert(key, used=max(delta, Decimal(0))).on_conflict_do_update(
            constraint="uq_discovery_budget_ledger_period_resource",
            set_={"used": func.greatest(Ledger.used + delta, 0), "updated_at": func.now()},
        )
        self._session.execute(stmt)

    def exhaust_ledger(self, key: LedgerKey) -> None:
        """Mark the counter exhausted so every later reservation in its period is denied."""
        stmt = self._upsert(key, used=Decimal(0), exhausted=True).on_conflict_do_update(
            constraint="uq_discovery_budget_ledger_period_resource",
            set_={"exhausted": True, "updated_at": func.now()},
        )
        self._session.execute(stmt)

    def ledger_states(self, keys: Collection[LedgerKey]) -> dict[LedgerKey, LedgerState]:
        """Return the stored state of each of ``keys`` that has a row."""
        pairs = [(key.period, key.resource) for key in keys]
        stmt = select(Ledger.period, Ledger.resource, Ledger.used, Ledger.exhausted).where(
            tuple_(Ledger.period, Ledger.resource).in_(pairs)
        )
        return {
            LedgerKey(period, resource): LedgerState(used, exhausted)
            for period, resource, used, exhausted in self._session.execute(stmt)
        }
