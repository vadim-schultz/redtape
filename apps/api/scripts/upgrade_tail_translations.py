"""Queue Azure upgrades for the tail rows that Workers AI wrote, while Azure has no ready work.

An operator runs this once a tail locale is live, or whenever Azure has spare capacity. Each run queues at most
``--limit`` upgrades and the next run takes the rest; a row with an open task keeps that task, and nothing is queued
at the database soft limit. The upgrade is ordinary completion: an Azure translation of the same unit supersedes the
tail row, and a human translation is never replaced.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass

from app.db import SessionLocal
from app.features.discovery.db_headroom import db_headroom
from app.features.search.clock import utc_now
from app.features.translation.enqueue import UPGRADE_SWEEP_LIMIT, TranslationEnqueuer
from sqlalchemy.orm import Session

from scripts.backfill_common import Headroom, StopReason, room_stop


@dataclass(slots=True)
class UpgradeReport:
    """How many upgrades one run queued, and why it stopped."""

    queued: int = 0
    stopped: StopReason = StopReason.FINISHED


def run_upgrade(session: Session, limit: int, headroom: Headroom) -> UpgradeReport:
    """Queue up to ``limit`` upgrades and commit them, unless the database is at its soft limit."""
    if (stop := room_stop(headroom)) is not None:
        return UpgradeReport(stopped=stop)
    queued = TranslationEnqueuer(session).enqueue_upgrades(utc_now(), limit)
    session.commit()
    return UpgradeReport(queued=queued)


def format_report(report: UpgradeReport) -> str:
    """Return the run as one line: how many were queued and why the run stopped."""
    return f"queued={report.queued} stopped={report.stopped.value}"


def _parse_limit(argv: Sequence[str] | None) -> int:
    parser = argparse.ArgumentParser(description="Queue Azure upgrades for tail translations while Azure is idle.")
    parser.add_argument("--limit", type=int, default=UPGRADE_SWEEP_LIMIT, help="most upgrades to queue in this run")
    limit: int = parser.parse_args(argv).limit
    return limit


def main(argv: Sequence[str] | None = None) -> int:
    """Run one upgrade sweep against the configured database and print its report."""
    limit = _parse_limit(argv)
    with SessionLocal() as session:
        report = run_upgrade(session, limit, db_headroom)
    print(format_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
