"""Budget ledger payloads exchanged with the machine API."""

from __future__ import annotations

from typing import Literal, TypeGuard, get_args

from pydantic import BaseModel

BudgetResource = Literal["r2_class_a", "r2_class_b", "browser_seconds", "neurons", "actions_minutes"]
BUDGET_RESOURCES: tuple[BudgetResource, ...] = get_args(BudgetResource)


def is_budget_resource(name: str) -> TypeGuard[BudgetResource]:
    """Return whether ``name`` is a resource the ledger guards."""
    return name in BUDGET_RESOURCES


class BudgetRow(BaseModel):
    """One resource in its current period."""

    resource: BudgetResource
    period: str
    cap: int
    used: float
    remaining: float
    exhausted: bool


class BudgetSnapshot(BaseModel):
    """Every resource in its current period."""

    items: list[BudgetRow]


class BudgetReservation(BaseModel):
    """The ledger's answer to a reservation; a denial arrives as HTTP 409 with ``granted`` false."""

    granted: bool
    remaining: float
