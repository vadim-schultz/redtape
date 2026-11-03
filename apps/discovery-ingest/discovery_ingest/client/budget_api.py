"""Budget routes: read the ledger, reserve before spending, correct the reservation and mark a quota exhausted."""

from __future__ import annotations

from discovery_ingest.budget_models import BudgetReservation, BudgetResource, BudgetRow, BudgetSnapshot
from discovery_ingest.client.http_client import MachineHttpClient

HTTP_CONFLICT = 409


class BudgetAPI:
    """Read and change the budget ledger."""

    def __init__(self, http: MachineHttpClient) -> None:
        """Keep the shared HTTP client."""
        self._http = http

    def snapshot(self) -> BudgetSnapshot:
        """Return every budget resource in its current period."""
        return self._http.request_model(BudgetSnapshot, "GET", "/budgets")

    def reserve(self, resource: BudgetResource, amount: float) -> BudgetReservation:
        """Reserve ``amount`` of ``resource``; a denial (409) is an answer, not an error."""
        return self._http.request_model(
            BudgetReservation,
            "POST",
            f"/budgets/{resource}/reserve",
            json={"amount": amount},
            allow=(HTTP_CONFLICT,),
        )

    def adjust(self, resource: BudgetResource, delta: float) -> BudgetRow:
        """Apply a signed correction to ``resource`` once its real cost is known."""
        return self._http.request_model(BudgetRow, "POST", f"/budgets/{resource}/adjust", json={"delta": delta})

    def exhaust(self, resource: BudgetResource) -> BudgetRow:
        """Mark ``resource`` exhausted for the rest of its period."""
        return self._http.request_model(BudgetRow, "POST", f"/budgets/{resource}/exhaust")
