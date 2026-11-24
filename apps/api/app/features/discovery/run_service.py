"""Worker-run lifecycle: start and finish explicit run records."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.features.discovery.errors import RunAlreadyFinishedError
from app.features.discovery.lookups import require_run
from app.features.discovery.repository import DiscoveryRepository, RunReport
from app.models.discovery import DiscoveryRun, DiscoveryRunStage, DiscoveryRunStatus
from app.schema.discovery.machine import RunFinishRequest, RunRead, RunStartRequest


def _run_read(run: DiscoveryRun) -> RunRead:
    return RunRead(id=run.id, kind=run.kind, status=run.status, started_at=run.started_at, finished_at=run.finished_at)


def _spend(body: RunFinishRequest) -> dict[str, float] | None:
    return None if body.spend is None else {resource: amount for resource, amount in body.spend.items()}


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
        spend=_spend(body),
    )


class DiscoveryRunService:
    """Record bounded worker runs through the machine API."""

    def __init__(self, repository: DiscoveryRepository) -> None:
        """Bind the service to ``repository``."""
        self._repo = repository

    def start(self, body: RunStartRequest) -> RunRead:
        """Close any run that never got its finish, then open a ``running`` record for the stage the request names."""
        now = datetime.now(UTC)
        self._repo.close_stale_runs(now=now)
        stage = body.stage or DiscoveryRunStage(body.kind.value)
        return _run_read(self._repo.insert_run(body.kind, stage, started_at=now))

    def finish(self, run_id: UUID, body: RunFinishRequest) -> RunRead:
        """Close ``run_id`` with the worker's report; a finished run stays immutable."""
        run = require_run(self._repo, run_id)
        if run.status != DiscoveryRunStatus.RUNNING.value:
            raise RunAlreadyFinishedError()
        closed = self._repo.close_run(run, _run_report(body), finished_at=datetime.now(UTC))
        return _run_read(closed)
