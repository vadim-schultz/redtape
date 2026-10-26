"""Budget ledger policy: who may spend a free allocation, and what is left of it."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from app.config import Settings, settings
from app.features.discovery.budget_resources import RESOURCE_SPECS, BudgetResource
from app.features.discovery.repository import DiscoveryRepository, LedgerKey, LedgerState

NO_USAGE = LedgerState(used=Decimal(0), exhausted=False)


@dataclass(frozen=True, slots=True)
class BudgetStatus:
    """One resource in its current period."""

    resource: BudgetResource
    period: str
    cap: int
    used: Decimal
    exhausted: bool

    @property
    def remaining(self) -> Decimal:
        """Capacity left, never negative (a correction may push ``used`` past the cap)."""
        return max(Decimal(self.cap) - self.used, Decimal(0))


@dataclass(frozen=True, slots=True)
class Reservation:
    """The answer to a reservation: whether it was granted and what is left afterwards."""

    granted: bool
    remaining: Decimal


def _key(resource: BudgetResource, now: datetime) -> LedgerKey:
    return LedgerKey(RESOURCE_SPECS[resource].period(now.astimezone(UTC)), resource.value)


class BudgetService:
    """Reserve, correct and exhaust the caps of free allocations; the period always comes from UTC ``now``."""

    def __init__(self, repository: DiscoveryRepository, caps: Settings = settings) -> None:
        """Bind the service to ``repository`` and the ``caps`` it enforces."""
        self._repo = repository
        self._caps = caps

    def snapshot(self, now: datetime) -> list[BudgetStatus]:
        """Return every resource with its usage in the period containing ``now``."""
        keys = {resource: _key(resource, now) for resource in BudgetResource}
        states = self._repo.ledger_states(keys.values())
        return [self._status(resource, keys[resource], states.get(keys[resource], NO_USAGE)) for resource in keys]

    def status(self, resource: BudgetResource, now: datetime) -> BudgetStatus:
        """Return ``resource`` in the period containing ``now``."""
        key = _key(resource, now)
        return self._status(resource, key, self._repo.ledger_states([key]).get(key, NO_USAGE))

    def reserve(self, resource: BudgetResource, amount: Decimal, now: datetime) -> Reservation:
        """Atomically add ``amount`` to the usage unless that would pass the cap or the period is exhausted."""
        cap = RESOURCE_SPECS[resource].cap(self._caps)
        granted = amount <= cap and self._repo.reserve_ledger(_key(resource, now), amount, cap)
        return Reservation(granted, self.status(resource, now).remaining)

    def adjust(self, resource: BudgetResource, delta: Decimal, now: datetime) -> BudgetStatus:
        """Record the real cost: apply a signed ``delta`` (never below zero, never refused)."""
        self._repo.adjust_ledger(_key(resource, now), delta)
        return self.status(resource, now)

    def exhaust(self, resource: BudgetResource, now: datetime) -> BudgetStatus:
        """Deny every further reservation of ``resource`` until its period rolls over."""
        self._repo.exhaust_ledger(_key(resource, now))
        return self.status(resource, now)

    def _status(self, resource: BudgetResource, key: LedgerKey, state: LedgerState) -> BudgetStatus:
        cap = RESOURCE_SPECS[resource].cap(self._caps)
        return BudgetStatus(resource, key.period, cap, state.used, state.exhausted)
