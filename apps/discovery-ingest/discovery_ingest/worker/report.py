"""The drain report every worker drain prints: the tally, why it stopped and what is still queued."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict

import httpx
from pydantic import ValidationError

from discovery_ingest.client import DiscoveryMachineApiError
from discovery_ingest.schemas import DrainReport
from discovery_ingest.worker.drain_loop import Finish
from discovery_ingest.worker.tally import Tally


def remaining_of(read: Callable[[], int]) -> int | None:
    """Return the ready backlog ``read`` reports, or ``None`` when the queue summary is unavailable."""
    try:
        return read()
    except (DiscoveryMachineApiError, httpx.HTTPError, ValidationError):
        return None


def build_report(tally: Tally, finish: Finish, remaining: int | None) -> DrainReport:
    """Return the report of a finished drain; ``remaining`` is ``None`` when the queue summary was unavailable."""
    return DrainReport(
        **asdict(tally),
        remaining=remaining,
        remaining_unknown=remaining is None,
        stop_reason=finish.reason,
        succeeded=finish.reason != "error",
        error=finish.error,
    )
