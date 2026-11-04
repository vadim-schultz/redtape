"""``budget show`` and ``budget report-minutes``: read the ledger against requirements, record minutes spent."""

from __future__ import annotations

from dataclasses import dataclass

from discovery_ingest.budget import BudgetGuard
from discovery_ingest.budget_models import BudgetResource, BudgetRow
from discovery_ingest.client import DiscoveryIngestClient

Requirement = tuple[BudgetResource, float]
"""A resource and the amount that must remain of it."""


@dataclass(frozen=True, slots=True)
class BudgetView:
    """The ledger rows the caller asked for, and the resources that are short of their requirement."""

    rows: list[BudgetRow]
    short: list[str]


def is_short(row: BudgetRow, needed: float) -> bool:
    """Return whether the row is exhausted or has less than ``needed`` remaining."""
    return row.exhausted or row.remaining < needed


def short_resources(rows: list[BudgetRow], requirements: list[Requirement]) -> list[str]:
    """Return the names of the required resources that are short, in ledger order."""
    needed = dict(requirements)
    return [row.resource for row in rows if row.resource in needed and is_short(row, needed[row.resource])]


def budget_view(
    client: DiscoveryIngestClient, resources: list[BudgetResource], requirements: list[Requirement]
) -> BudgetView | None:
    """Return the filtered ledger and its short resources, or ``None`` when the ledger is unreachable."""
    snapshot = BudgetGuard(client.budget).snapshot()
    if snapshot is None:
        return None
    shown = [row for row in snapshot.items if not resources or row.resource in resources]
    return BudgetView(shown, short_resources(snapshot.items, requirements))


def record_minutes(client: DiscoveryIngestClient, minutes: int) -> bool:
    """Add ``minutes`` of Actions time to the ledger; return ``False`` when the ledger is unreachable."""
    return BudgetGuard(client.budget).adjust("actions_minutes", minutes)
