"""The ledger-backed meter that caps what the object store may do (chapter 23)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from app.config import Settings
from app.features.discovery.budget_meter import OPERATION_RESOURCE, ledger_meter
from app.features.discovery.budget_resources import BudgetResource
from app.features.discovery.budgets import BudgetService, Reservation
from app.features.discovery.repository import DiscoveryRepository
from app.shared.object_store import (
    InMemoryObjectStore,
    MeteredObjectStore,
    ObjectStore,
    ObjectStoreQuotaError,
    ObjectStoreUnavailableError,
)
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from test_discovery_artifacts_api import ExplodingStore

NOW = datetime(2026, 10, 26, 12, 0, tzinfo=UTC)


def _budgets(session: Session, **caps: int) -> BudgetService:
    return BudgetService(DiscoveryRepository(session), Settings(_env_file=None, **caps))


def _used(budgets: BudgetService, resource: BudgetResource) -> Decimal:
    return budgets.status(resource, NOW).used


def test_put_and_delete_reserve_class_a_get_and_exists_reserve_class_b_and_presign_reserves_nothing(
    db_session: Session,
) -> None:
    budgets = _budgets(db_session)
    store = MeteredObjectStore(InMemoryObjectStore(), ledger_meter(budgets, lambda: NOW))

    store.put("k", b"x", "text/plain")
    store.delete("k")
    store.put("k", b"x", "text/plain")
    store.get("k")
    store.exists("k")
    store.presigned_get_url("k")

    assert _used(budgets, BudgetResource.R2_CLASS_A) == 3
    assert _used(budgets, BudgetResource.R2_CLASS_B) == 2


def test_every_operation_class_maps_to_a_ledger_resource() -> None:
    assert OPERATION_RESOURCE == {"class_a": BudgetResource.R2_CLASS_A, "class_b": BudgetResource.R2_CLASS_B}


def _put(store: ObjectStore) -> object:
    return store.put("k", b"x", "text/plain")


def _delete(store: ObjectStore) -> object:
    return store.delete("k")


def _get(store: ObjectStore) -> object:
    return store.get("k")


def _exists(store: ObjectStore) -> object:
    return store.exists("k")


@pytest.mark.parametrize("operation", [_put, _delete])
def test_a_denied_class_a_reservation_raises_before_the_inner_store_is_touched(
    db_session: Session, operation: Callable[[ObjectStore], object]
) -> None:
    budgets = _budgets(db_session, budget_r2_class_a_monthly=0)
    store = MeteredObjectStore(ExplodingStore(), ledger_meter(budgets, lambda: NOW))

    with pytest.raises(ObjectStoreQuotaError):
        operation(store)

    assert _used(budgets, BudgetResource.R2_CLASS_A) == 0


@pytest.mark.parametrize("operation", [_get, _exists])
def test_a_denied_class_b_reservation_raises_before_the_inner_store_is_touched(
    db_session: Session, operation: Callable[[ObjectStore], object]
) -> None:
    budgets = _budgets(db_session, budget_r2_class_b_monthly=1)
    store = MeteredObjectStore(InMemoryObjectStore(), ledger_meter(budgets, lambda: NOW))
    store.exists("k")
    exploding = MeteredObjectStore(ExplodingStore(), ledger_meter(budgets, lambda: NOW))

    with pytest.raises(ObjectStoreQuotaError):
        operation(exploding)

    assert _used(budgets, BudgetResource.R2_CLASS_B) == 1


class _BrokenLedger:
    """A budget service whose database write fails."""

    def reserve(self, resource: BudgetResource, amount: Decimal, now: datetime) -> Reservation:
        raise OperationalError("INSERT", {}, ConnectionError("ledger down"))


def test_a_ledger_write_failure_refuses_the_operation_instead_of_letting_it_through() -> None:
    meter = ledger_meter(_BrokenLedger(), lambda: NOW)
    store = MeteredObjectStore(ExplodingStore(), meter)

    with pytest.raises(ObjectStoreUnavailableError) as raised:
        store.put("k", b"x", "text/plain")

    assert not isinstance(raised.value, ObjectStoreQuotaError)
