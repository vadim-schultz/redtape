"""Usage counter for one free allocation in one day or month."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import Boolean, Numeric, String, UniqueConstraint, Uuid, false
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.discovery.mixins import TimestampMixin


class DiscoveryBudgetLedger(TimestampMixin, Base):
    """What a resource has spent in one period; ``period`` is ``YYYY-MM-DD`` (daily) or ``YYYY-MM`` (monthly)."""

    __tablename__ = "discovery_budget_ledger"
    __table_args__ = (UniqueConstraint("period", "resource", name="uq_discovery_budget_ledger_period_resource"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    period: Mapped[str] = mapped_column(String(10), nullable=False)
    resource: Mapped[str] = mapped_column(String(40), nullable=False)
    used: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal(0), server_default="0")
    exhausted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
