"""``budget show`` and ``budget report-minutes``: thin command line wrappers over the budget guard."""

from __future__ import annotations

import argparse
import json
import sys

from discovery_ingest.api_client import DiscoveryMachineClient
from discovery_ingest.budget import BudgetGuard
from discovery_ingest.budget_models import BUDGET_RESOURCES, BudgetResource, BudgetRow, is_budget_resource
from discovery_ingest.cli_errors import failing_with_api_error
from discovery_ingest.config import load_ingest_settings

EXIT_SHORT = 3
EXIT_LEDGER_UNAVAILABLE_STRICT = 4
Requirement = tuple[BudgetResource, float]


def _resource_arg(raw: str) -> BudgetResource:
    if not is_budget_resource(raw):
        raise argparse.ArgumentTypeError(f"expected one of {', '.join(BUDGET_RESOURCES)}; got {raw!r}")
    return raw


def _requirement_arg(raw: str) -> Requirement:
    """Parse ``RESOURCE=N`` into a resource and a non-negative amount."""
    name, _, amount = raw.partition("=")
    try:
        needed = float(amount)
    except ValueError:
        needed = -1.0
    if needed < 0:
        raise argparse.ArgumentTypeError(f"expected RESOURCE=N with N >= 0; got {raw!r}")
    return _resource_arg(name), needed


def _positive_minutes(raw: str) -> int:
    if not raw.isdigit() or int(raw) < 1:
        raise argparse.ArgumentTypeError(f"expected a positive whole number of minutes; got {raw!r}")
    return int(raw)


def register_budget_parser(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Add the ``budget`` command with its ``show`` and ``report-minutes`` subcommands."""
    budget = sub.add_parser("budget", help="Free-allocation budget ledger")
    budget_sub = budget.add_subparsers(dest="budget_command")
    show = budget_sub.add_parser("show", help="Print the ledger; exit 3 when a required resource is short")
    show.add_argument("--resource", type=_resource_arg, action="append", help="Only print this resource (repeatable)")
    show.add_argument(
        "--require-remaining",
        type=_requirement_arg,
        action="append",
        default=[],
        metavar="RESOURCE=N",
        help="Exit 3 when RESOURCE has less than N remaining or is exhausted (repeatable)",
    )
    show.add_argument("--strict", action="store_true", help="Exit 4 instead of 0 when the ledger is unreachable")
    minutes = budget_sub.add_parser("report-minutes", help="Add Actions minutes spent by this run to the ledger")
    minutes.add_argument("--minutes", type=_positive_minutes, required=True)


def _guard() -> BudgetGuard:
    settings = load_ingest_settings()
    return BudgetGuard(DiscoveryMachineClient(settings.discovery_api_url, settings.discovery_api_key))


def _is_short(row: BudgetRow, needed: float) -> bool:
    return row.exhausted or row.remaining < needed


def _short_resources(rows: list[BudgetRow], requirements: list[Requirement]) -> list[str]:
    needed = dict(requirements)
    return [row.resource for row in rows if row.resource in needed and _is_short(row, needed[row.resource])]


def _show(args: argparse.Namespace) -> int:
    snapshot = _guard().snapshot()
    if snapshot is None:
        print("budget ledger unreachable; budgets were not checked", file=sys.stderr)
        return EXIT_LEDGER_UNAVAILABLE_STRICT if args.strict else 0
    shown = [row for row in snapshot.items if not args.resource or row.resource in args.resource]
    print(json.dumps({"items": [row.model_dump(mode="json") for row in shown]}))
    short = _short_resources(snapshot.items, args.require_remaining)
    if short:
        print(f"budget short or exhausted: {', '.join(short)}", file=sys.stderr)
        return EXIT_SHORT
    return 0


def _report_minutes(args: argparse.Namespace) -> int:
    if not _guard().adjust("actions_minutes", args.minutes):
        print("budget ledger unreachable; the minutes were not recorded", file=sys.stderr)
    return 0


budget_show = failing_with_api_error("budget", _show)
budget_report_minutes = failing_with_api_error("budget", _report_minutes)
