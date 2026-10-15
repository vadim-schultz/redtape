"""Pure calendar router for the platform-maintenance GitHub Actions workflow."""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, date, datetime
from typing import Literal

MaintenanceJob = Literal["openplz", "discovery", "skip"]

DEFAULT_MAINTENANCE_ANCHOR_DATE = date(2026, 1, 1)
_VALID_DISPATCH_JOBS: frozenset[MaintenanceJob] = frozenset({"openplz", "discovery", "skip"})


def days_since_anchor(on_date: date, anchor: date) -> int:
    """Return whole calendar days from ``anchor`` to ``on_date`` (``on_date - anchor``)."""

    return (on_date - anchor).days


def scheduled_job_for_cycle_day(days_mod_6: int) -> MaintenanceJob:
    """Map ``days_since_anchor % 6`` to the maintenance job for that cycle day."""

    if days_mod_6 == 0:
        return "openplz"
    if days_mod_6 == 3:
        return "discovery"
    return "skip"


def resolve_maintenance_job(
    on_date: date,
    anchor: date,
    dispatch_override: str | None,
) -> MaintenanceJob:
    """Resolve which job to run for ``on_date``, honoring an optional manual override."""

    if dispatch_override is not None and dispatch_override != "":
        if dispatch_override not in _VALID_DISPATCH_JOBS:
            raise ValueError(f"invalid dispatch job: {dispatch_override!r}")
        return dispatch_override

    cycle_day = days_since_anchor(on_date, anchor) % 6
    return scheduled_job_for_cycle_day(cycle_day)


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _today_utc() -> date:
    return datetime.now(UTC).date()


def main(argv: list[str] | None = None) -> int:
    """Print the resolved maintenance job name for GitHub Actions routing."""

    parser = argparse.ArgumentParser(description="Resolve platform maintenance job for today or a given date.")
    parser.add_argument(
        "--anchor",
        default=DEFAULT_MAINTENANCE_ANCHOR_DATE.isoformat(),
        help="Anchor date (UTC) for the 6-day cycle (default: 2026-01-01).",
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Date to evaluate (UTC ISO); default is today in UTC.",
    )
    parser.add_argument(
        "--dispatch-job",
        default=None,
        dest="dispatch_job",
        help="workflow_dispatch override: openplz, discovery, or skip.",
    )
    args = parser.parse_args(argv)

    on_date = _parse_date(args.date) if args.date else _today_utc()
    anchor = _parse_date(args.anchor)
    job = resolve_maintenance_job(on_date, anchor, args.dispatch_job)
    print(job)
    return 0


if __name__ == "__main__":
    sys.exit(main())
