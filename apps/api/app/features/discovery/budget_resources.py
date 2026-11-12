"""The free allocations the ledger guards: their periods and where each cap comes from."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from app.config import Settings


class BudgetResource(StrEnum):
    """Names a worker or the object store can reserve against."""

    R2_CLASS_A = "r2_class_a"
    R2_CLASS_B = "r2_class_b"
    BROWSER_SECONDS = "browser_seconds"
    NEURONS = "neurons"
    ACTIONS_MINUTES = "actions_minutes"
    AZURE_TRANSLATOR_CHARS = "azure_translator_chars"


DAILY_PERIOD = "%Y-%m-%d"
MONTHLY_PERIOD = "%Y-%m"


@dataclass(frozen=True, slots=True)
class ResourceSpec:
    """How a resource is counted: the UTC period format and the cap taken from settings."""

    period_format: str
    cap: Callable[[Settings], int]

    def period(self, now: datetime) -> str:
        """Return the period key that ``now`` (a UTC instant) falls into."""
        return now.strftime(self.period_format)


def _actions_minutes_cap(settings: Settings) -> int:
    return max(settings.budget_actions_minutes_monthly - settings.actions_ci_reserve_minutes, 0)


RESOURCE_SPECS: dict[BudgetResource, ResourceSpec] = {
    BudgetResource.R2_CLASS_A: ResourceSpec(MONTHLY_PERIOD, lambda s: s.budget_r2_class_a_monthly),
    BudgetResource.R2_CLASS_B: ResourceSpec(MONTHLY_PERIOD, lambda s: s.budget_r2_class_b_monthly),
    BudgetResource.BROWSER_SECONDS: ResourceSpec(DAILY_PERIOD, lambda s: s.budget_browser_seconds_daily),
    BudgetResource.NEURONS: ResourceSpec(DAILY_PERIOD, lambda s: s.budget_neurons_daily),
    BudgetResource.ACTIONS_MINUTES: ResourceSpec(MONTHLY_PERIOD, _actions_minutes_cap),
    BudgetResource.AZURE_TRANSLATOR_CHARS: ResourceSpec(
        MONTHLY_PERIOD, lambda s: s.budget_azure_translator_chars_monthly
    ),
}
