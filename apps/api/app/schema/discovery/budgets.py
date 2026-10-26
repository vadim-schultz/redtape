"""Request and response models for the budget ledger routes."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field

MAX_AMOUNT = Decimal(10**9)
"""Larger than any real cost and far below the ``Numeric(14, 2)`` column, so a typo cannot overflow it."""

Amount = Annotated[Decimal, Field(gt=0, le=MAX_AMOUNT, allow_inf_nan=False)]
Delta = Annotated[Decimal, Field(ge=-MAX_AMOUNT, le=MAX_AMOUNT, allow_inf_nan=False)]


class BudgetReserveRequest(BaseModel):
    """Capacity a worker wants to spend."""

    amount: Amount


class BudgetAdjustRequest(BaseModel):
    """A signed correction once the real cost is known."""

    delta: Delta


class BudgetReserveResponse(BaseModel):
    """Whether the reservation was granted and what is left of the period."""

    granted: bool
    remaining: float


class BudgetRead(BaseModel):
    """One resource in its current period."""

    resource: str
    period: str
    cap: int
    used: float
    remaining: float
    exhausted: bool


class BudgetListResponse(BaseModel):
    """Every resource in its current period."""

    items: list[BudgetRead]


class AdminBudgetListResponse(BudgetListResponse):
    """The snapshot plus the live stored-bytes figure and its cap (a sum, not a ledger counter)."""

    stored_bytes: int
    stored_bytes_cap: int
