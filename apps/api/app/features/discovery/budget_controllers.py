"""HTTP handlers for the budget ledger: machine reservations and the admin snapshot."""

from __future__ import annotations

from litestar import Controller, Response, get, post
from litestar.status_codes import HTTP_200_OK, HTTP_409_CONFLICT

from app.features.discovery.budget_access import BudgetApiService
from app.features.discovery.guards import DISCOVERY_ADMIN_GUARDS, require_discovery_machine
from app.schema.discovery.budgets import (
    AdminBudgetListResponse,
    BudgetAdjustRequest,
    BudgetListResponse,
    BudgetRead,
    BudgetReserveRequest,
    BudgetReserveResponse,
)


class DiscoveryBudgetMachineController(Controller):
    """Workers read the remaining budget before spending and report spend afterwards."""

    path = "/budgets"
    guards = [require_discovery_machine]

    @get("/", sync_to_thread=True)
    def list_budgets(self, discovery_budget_api_service: BudgetApiService) -> BudgetListResponse:
        """Return every budget resource in its current period, for workers to read before they spend."""
        return discovery_budget_api_service.snapshot()

    @post("/{resource:str}/reserve", sync_to_thread=True, status_code=HTTP_200_OK)
    def reserve_budget(
        self, discovery_budget_api_service: BudgetApiService, resource: str, data: BudgetReserveRequest
    ) -> Response[BudgetReserveResponse]:
        """Reserve an amount of a resource; answer 409 when the budget cannot grant it."""
        result = discovery_budget_api_service.reserve(resource, data.amount)
        return Response(result, status_code=HTTP_200_OK if result.granted else HTTP_409_CONFLICT)

    @post("/{resource:str}/adjust", sync_to_thread=True, status_code=HTTP_200_OK)
    def adjust_budget(
        self, discovery_budget_api_service: BudgetApiService, resource: str, data: BudgetAdjustRequest
    ) -> BudgetRead:
        """Apply a signed correction to a resource budget."""
        return discovery_budget_api_service.adjust(resource, data.delta)

    @post("/{resource:str}/exhaust", sync_to_thread=True, status_code=HTTP_200_OK)
    def exhaust_budget(self, discovery_budget_api_service: BudgetApiService, resource: str) -> BudgetRead:
        """Mark a resource exhausted for the current period."""
        return discovery_budget_api_service.exhaust(resource)


class DiscoveryBudgetAdminController(Controller):
    """Allowlisted operators see the same snapshot plus stored bytes."""

    path = "/budgets"
    guards = DISCOVERY_ADMIN_GUARDS

    @get("/", sync_to_thread=True)
    def admin_budgets(self, discovery_budget_api_service: BudgetApiService) -> AdminBudgetListResponse:
        """Return the budget snapshot with the live stored-bytes figure and its cap."""
        return discovery_budget_api_service.admin_snapshot()
