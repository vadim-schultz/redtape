"""Record a worker drain as an explicit run through the machine API."""

from __future__ import annotations

from discovery_ingest.api_client import DiscoveryMachineApiError, DiscoveryMachineClient
from discovery_ingest.schemas import DrainReport, RunFinishRequest, StopReason
from discovery_ingest.worker.drain import run_worker_drain
from discovery_ingest.worker.fetcher import PoliteUrlFetcher

_MAX_ERROR_DETAIL = 1000


def _succeeded(report: DrainReport, *, max_tasks: int) -> RunFinishRequest:
    stop_reason: StopReason = "batch_limit" if report.claimed >= max_tasks else "queue_empty"
    return RunFinishRequest(
        status="succeeded",
        claimed_count=report.claimed,
        completed_count=report.completed,
        failed_count=report.failed,
        skipped_count=report.skipped,
        stop_reason=stop_reason,
    )


def _failed(err: DiscoveryMachineApiError) -> RunFinishRequest:
    return RunFinishRequest(
        status="failed",
        claimed_count=0,
        completed_count=0,
        failed_count=0,
        skipped_count=0,
        stop_reason="error",
        error_detail=str(err)[:_MAX_ERROR_DETAIL],
    )


def run_recorded_drain(
    client: DiscoveryMachineClient,
    fetcher: PoliteUrlFetcher,
    *,
    max_tasks: int,
) -> DrainReport:
    """Drain one bounded batch between a run start and a run finish.

    Individual task failures stay in the report; only an API failure marks the run failed.
    """
    run_id = client.start_run()
    try:
        report = run_worker_drain(client, fetcher, max_tasks=max_tasks)
    except DiscoveryMachineApiError as err:
        client.finish_run(run_id, _failed(err))
        raise
    client.finish_run(run_id, _succeeded(report, max_tasks=max_tasks))
    return report
