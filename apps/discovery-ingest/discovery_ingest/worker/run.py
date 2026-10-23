"""Record a worker drain as an explicit run through the machine API."""

from __future__ import annotations

from discovery_ingest.api_client import DiscoveryMachineApiError, DiscoveryMachineClient
from discovery_ingest.schemas import DrainReport, RunFinishRequest
from discovery_ingest.worker.drain import run_worker_drain
from discovery_ingest.worker.fetcher import PoliteUrlFetcher
from discovery_ingest.worker.policy import DrainPolicy

_MAX_ERROR_DETAIL = 1000


def _succeeded(report: DrainReport) -> RunFinishRequest:
    return RunFinishRequest(
        status="succeeded",
        claimed_count=report.claimed,
        completed_count=report.completed,
        failed_count=report.failed,
        skipped_count=report.skipped,
        remaining_count=report.remaining,
        stop_reason=report.stop_reason,
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
    policy: DrainPolicy,
) -> DrainReport:
    """Drain bounded batches between a run start and a run finish.

    Individual task failures stay in the report; only an API failure marks the run failed.
    """
    run_id = client.start_run()
    try:
        report = run_worker_drain(client, fetcher, policy)
    except DiscoveryMachineApiError as err:
        client.finish_run(run_id, _failed(err))
        raise
    client.finish_run(run_id, _succeeded(report))
    return report.model_copy(update={"run_id": run_id})
