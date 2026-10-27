"""The object store meter backed by the budget ledger: it counts R2 operations against their monthly caps."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from decimal import Decimal
from typing import Protocol

from sqlalchemy.exc import SQLAlchemyError

from app.features.discovery.budget_resources import BudgetResource
from app.features.discovery.budgets import Reservation
from app.shared.object_store import ObjectStoreMeter, ObjectStoreQuotaError, ObjectStoreUnavailableError, OperationClass

OPERATION_RESOURCE: Mapping[OperationClass, BudgetResource] = {
    "class_a": BudgetResource.R2_CLASS_A,
    "class_b": BudgetResource.R2_CLASS_B,
}
"""Cloudflare bills writes and deletes as Class A, reads and heads as Class B."""


class BudgetReserver(Protocol):
    """What the meter needs from the ledger."""

    def reserve(self, resource: BudgetResource, amount: Decimal, now: datetime) -> Reservation:
        """Atomically reserve ``amount`` of ``resource`` at ``now``."""
        ...


def _utc_now() -> datetime:
    return datetime.now(UTC)


def ledger_meter(budgets: BudgetReserver, clock: Callable[[], datetime] = _utc_now) -> ObjectStoreMeter:
    """Return a meter that reserves each operation in the ledger.

    A denial raises :class:`ObjectStoreQuotaError`. A ledger that cannot be written raises
    :class:`ObjectStoreUnavailableError`: the meter fails closed, because an uncounted operation may bill.
    """

    def meter(operation: OperationClass, count: int) -> None:
        resource = OPERATION_RESOURCE[operation]
        try:
            granted = budgets.reserve(resource, Decimal(count), clock()).granted
        except SQLAlchemyError as err:
            raise ObjectStoreUnavailableError("Budget ledger is unavailable") from err
        if not granted:
            raise ObjectStoreQuotaError(f"Monthly {resource.value} budget is exhausted")

    return meter
