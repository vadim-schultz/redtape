"""Worker-run lifecycle: start and finish explicit run records."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.features.discovery.errors import RunAlreadyFinishedError
from app.features.discovery.lookups import require_run
from app.features.discovery.repository import DiscoveryRepository, RunReport
from app.models.discovery import DiscoveryRun, DiscoveryRunStatus
from app.schema.discovery.machine import RunFinishRequest, RunRead, RunStartRequest


def _run_read(run: DiscoveryRun) -> RunRead:
    return RunRead(id=run.id, kind=run.kind, status=run.status, started_at=run.started_at, finished_at=run.finished_at)


def _run_report(body: RunFinishRequest) -> RunReport:
    return RunReport(
        status=DiscoveryRunStatus(body.status),
        claimed_count=body.claimed_count,
        completed_count=body.completed_count,
        failed_count=body.failed_count,
        skipped_count=body.skipped_count,
        remaining_count=body.remaining_count,
        stop_reason=body.stop_reason,
        error_detail=body.error_detail,
    )


class DiscoveryRunService:
    """Record bounded worker runs through the machine API."""

    def __init__(self, repository: DiscoveryRepository) -> None:
        """Bind the service to ``repository``."""
        self._repo = repository

    def start(self, body: RunStartRequest) -> RunRead:
        """Open a ``running`` record."""
        return _run_read(self._repo.insert_run(body.kind, started_at=datetime.now(UTC)))

    def finish(self, run_id: UUID, body: RunFinishRequest) -> RunRead:
        """Close ``run_id`` with the worker's report; a finished run stays immutable."""
        run = require_run(self._repo, run_id)
        if run.status != DiscoveryRunStatus.RUNNING.value:
            raise RunAlreadyFinishedError()
        closed = self._repo.close_run(run, _run_report(body), finished_at=datetime.now(UTC))
        return _run_read(closed)
