"""Machine and admin views of the budget ledger."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from app.config import settings
from app.features.discovery.budget_resources import BudgetResource
from app.features.discovery.budgets import BudgetService, BudgetStatus, Reservation
from app.features.discovery.errors import DiscoveryNotFoundError
from app.features.discovery.repository import DiscoveryRepository
from app.schema.discovery.budgets import AdminBudgetListResponse, BudgetListResponse, BudgetRead, BudgetReserveResponse


class UnknownBudgetResourceError(DiscoveryNotFoundError):
    """The path names a resource the ledger does not guard."""

    def __init__(self, name: str) -> None:
        """Build the error naming ``name``."""
        super().__init__(f"Unknown budget resource: {name}")


def parse_resource(name: str) -> BudgetResource:
    """Return the resource called ``name`` or raise :class:`UnknownBudgetResourceError` (HTTP 404)."""
    try:
        return BudgetResource(name)
    except ValueError as err:
        raise UnknownBudgetResourceError(name) from err


class BudgetApiService:
    """Translate budget routes into ledger calls stamped with the current UTC time."""

    def __init__(self, repository: DiscoveryRepository, budgets: BudgetService) -> None:
        """Bind the service to ``repository`` (stored bytes) and the ledger ``budgets``."""
        self._repo = repository
        self._budgets = budgets

    def snapshot(self) -> BudgetListResponse:
        """Return every resource in its current period."""
        return BudgetListResponse(items=self._items())

    def admin_snapshot(self) -> AdminBudgetListResponse:
        """Return the snapshot with the live stored-bytes figure and its cap."""
        return AdminBudgetListResponse(
            items=self._items(),
            stored_bytes=self._repo.total_artifact_bytes(),
            stored_bytes_cap=settings.object_store_max_bytes,
        )

    def reserve(self, resource: str, amount: Decimal) -> BudgetReserveResponse:
        """Try to reserve ``amount`` of ``resource``."""
        reservation = self._budgets.reserve(parse_resource(resource), amount, _now())
        return _reserve_response(reservation)

    def adjust(self, resource: str, delta: Decimal) -> BudgetRead:
        """Apply a signed correction to ``resource``."""
        return _read(self._budgets.adjust(parse_resource(resource), delta, _now()))

    def exhaust(self, resource: str) -> BudgetRead:
        """Mark ``resource`` exhausted for the current period."""
        return _read(self._budgets.exhaust(parse_resource(resource), _now()))

    def _items(self) -> list[BudgetRead]:
        return [_read(status) for status in self._budgets.snapshot(_now())]


def _now() -> datetime:
    return datetime.now(UTC)


def _read(status: BudgetStatus) -> BudgetRead:
    return BudgetRead(
        resource=status.resource.value,
        period=status.period,
        cap=status.cap,
        used=float(status.used),
        remaining=float(status.remaining),
        exhausted=status.exhausted,
    )


def _reserve_response(reservation: Reservation) -> BudgetReserveResponse:
    return BudgetReserveResponse(granted=reservation.granted, remaining=float(reservation.remaining))
