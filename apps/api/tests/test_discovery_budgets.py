"""Budget ledger policy: atomic reservations, corrections, exhaustion and period rollover (chapter 23)."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from app.config import Settings
from app.db import engine
from app.features.discovery.budget_resources import BudgetResource
from app.features.discovery.budgets import BudgetService
from app.features.discovery.repository import DiscoveryRepository
from app.models.discovery import DiscoveryBudgetLedger
from sqlalchemy import delete
from sqlalchemy.orm import Session

NOON = datetime(2026, 10, 26, 12, 0, tzinfo=UTC)
NEURONS = BudgetResource.NEURONS
CLASS_A = BudgetResource.R2_CLASS_A


def _service(session: Session, **caps: int) -> BudgetService:
    return BudgetService(DiscoveryRepository(session), Settings(_env_file=None, **caps))


def test_reserve_within_the_cap_is_granted_and_counted(db_session: Session) -> None:
    service = _service(db_session)

    first = service.reserve(NEURONS, Decimal(3000), NOON)
    second = service.reserve(NEURONS, Decimal(5000), NOON)

    assert (first.granted, first.remaining) == (True, Decimal(5000))
    assert (second.granted, second.remaining) == (True, Decimal(0))
    assert service.status(NEURONS, NOON).used == Decimal(8000)


def test_reserve_that_would_pass_the_cap_is_denied_and_does_not_change_usage(db_session: Session) -> None:
    service = _service(db_session)
    service.reserve(NEURONS, Decimal(7000), NOON)

    denied = service.reserve(NEURONS, Decimal(1001), NOON)
    too_big_first = _service(db_session, budget_browser_seconds_daily=100).reserve(
        BudgetResource.BROWSER_SECONDS, Decimal(101), NOON
    )

    assert (denied.granted, denied.remaining) == (False, Decimal(1000))
    assert service.status(NEURONS, NOON).used == Decimal(7000)
    assert too_big_first.granted is False
    assert _service(db_session).status(BudgetResource.BROWSER_SECONDS, NOON).used == Decimal(0)


@pytest.mark.parametrize(
    ("resource", "before", "after"),
    [
        (NEURONS, datetime(2026, 10, 26, 23, 59, tzinfo=UTC), datetime(2026, 10, 27, 0, 0, tzinfo=UTC)),
        (CLASS_A, datetime(2026, 10, 31, 23, 59, tzinfo=UTC), datetime(2026, 11, 1, 0, 0, tzinfo=UTC)),
    ],
)
def test_reserve_after_exhaust_is_denied_until_the_period_rolls_over(
    db_session: Session, resource: BudgetResource, before: datetime, after: datetime
) -> None:
    service = _service(db_session)
    service.exhaust(resource, before)

    assert service.reserve(resource, Decimal(1), before).granted is False
    assert service.status(resource, before).exhausted is True
    assert service.reserve(resource, Decimal(1), after).granted is True
    assert service.status(resource, after).exhausted is False


def test_reserve_in_the_same_period_after_a_mid_period_exhaust_stays_denied(db_session: Session) -> None:
    service = _service(db_session)
    service.reserve(NEURONS, Decimal(10), NOON)
    service.exhaust(NEURONS, NOON)

    assert service.reserve(NEURONS, Decimal(1), datetime(2026, 10, 26, 23, 0, tzinfo=UTC)).granted is False


def test_adjust_with_a_negative_delta_never_goes_below_zero(db_session: Session) -> None:
    service = _service(db_session)
    service.reserve(NEURONS, Decimal(100), NOON)

    assert service.adjust(NEURONS, Decimal(-30), NOON).used == Decimal(70)
    assert service.adjust(NEURONS, Decimal(-500), NOON).used == Decimal(0)
    assert service.adjust(BudgetResource.BROWSER_SECONDS, Decimal(-5), NOON).used == Decimal(0)


def test_adjust_is_never_refused_even_past_the_cap(db_session: Session) -> None:
    service = _service(db_session)

    over = service.adjust(NEURONS, Decimal(9000), NOON)

    assert (over.used, over.remaining) == (Decimal(9000), Decimal(0))
    assert service.reserve(NEURONS, Decimal(1), NOON).granted is False


def test_snapshot_lists_every_resource_with_zero_for_unused_and_remaining_clamped(db_session: Session) -> None:
    service = _service(db_session)
    service.adjust(NEURONS, Decimal(9000), NOON)

    rows = {row.resource: row for row in service.snapshot(NOON)}

    assert set(rows) == set(BudgetResource)
    assert (rows[NEURONS].used, rows[NEURONS].remaining, rows[NEURONS].cap) == (Decimal(9000), Decimal(0), 8000)
    assert (rows[NEURONS].period, rows[CLASS_A].period) == ("2026-10-26", "2026-10")
    assert (rows[CLASS_A].used, rows[CLASS_A].remaining, rows[CLASS_A].exhausted) == (0, 400_000, False)


def test_actions_minutes_cap_is_the_monthly_cap_minus_the_ci_reserve(db_session: Session) -> None:
    default = _service(db_session).status(BudgetResource.ACTIONS_MINUTES, NOON)
    tuned = _service(db_session, budget_actions_minutes_monthly=900, actions_ci_reserve_minutes=100)
    reserve_over = _service(db_session, budget_actions_minutes_monthly=500, actions_ci_reserve_minutes=600)

    assert default.cap == 400
    assert tuned.status(BudgetResource.ACTIONS_MINUTES, NOON).cap == 800
    assert reserve_over.status(BudgetResource.ACTIONS_MINUTES, NOON).cap == 0
    assert reserve_over.reserve(BudgetResource.ACTIONS_MINUTES, Decimal(1), NOON).granted is False


RACE_NOW = datetime(2099, 1, 1, 12, 0, tzinfo=UTC)


@pytest.fixture
def committed_ledger() -> Iterator[None]:
    """Real committed rows for the race test; removed afterwards because the shared fixture rolls back instead."""
    yield
    with Session(engine) as cleanup:
        cleanup.execute(delete(DiscoveryBudgetLedger).where(DiscoveryBudgetLedger.period.like("2099-%")))
        cleanup.commit()


def _reserve_in_own_session(granted: list[bool], gate: threading.Barrier) -> None:
    with Session(engine) as session:
        service = _service(session, budget_neurons_daily=10)
        gate.wait()
        granted.append(service.reserve(NEURONS, Decimal(6), RACE_NOW).granted)
        session.commit()


def test_two_reservations_racing_for_the_last_capacity_grant_exactly_one(committed_ledger: None) -> None:
    with Session(engine) as seed:
        _service(seed, budget_neurons_daily=10).adjust(NEURONS, Decimal(0), RACE_NOW)
        seed.commit()
    granted: list[bool] = []
    gate = threading.Barrier(2)
    threads = [threading.Thread(target=_reserve_in_own_session, args=(granted, gate)) for _ in range(2)]

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert sorted(granted) == [False, True]
    with Session(engine) as check:
        assert _service(check, budget_neurons_daily=10).status(NEURONS, RACE_NOW).used == Decimal(6)
