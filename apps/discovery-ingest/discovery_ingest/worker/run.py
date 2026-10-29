"""Record a worker drain as an explicit run through the machine API."""

from __future__ import annotations

from discovery_ingest.api_client import DiscoveryMachineApiError, DiscoveryMachineClient
from discovery_ingest.browser.port import BrowserClient
from discovery_ingest.schemas import DrainReport, RunFinishRequest
from discovery_ingest.worker.drain import run_worker_drain
from discovery_ingest.worker.fetcher import PoliteUrlFetcher
from discovery_ingest.worker.llm_enqueue import LlmEnqueuer
from discovery_ingest.worker.llm_extract import AfterExtract, no_after_extract
from discovery_ingest.worker.llm_runtime import LlmResources
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


def _failed(detail: str) -> RunFinishRequest:
    return RunFinishRequest(
        status="failed",
        claimed_count=0,
        completed_count=0,
        failed_count=0,
        skipped_count=0,
        stop_reason="error",
        error_detail=detail[:_MAX_ERROR_DETAIL],
    )


def _finish_request(report: DrainReport) -> RunFinishRequest:
    """A drain that ended on an infrastructure error (``error``) is a failed run; every other stop succeeded."""
    return _succeeded(report) if report.succeeded else _failed(report.error or "the drain stopped on an error")


def run_recorded_drain(
    client: DiscoveryMachineClient,
    fetcher: PoliteUrlFetcher,
    policy: DrainPolicy,
    *,
    browser: BrowserClient | None = None,
    llm: LlmResources | None = None,
    after_extract: AfterExtract = no_after_extract,
    llm_enqueue: LlmEnqueuer | None = None,
) -> DrainReport:
    """Drain bounded batches between a run start and a run finish.

    Individual task failures stay in the report; an API failure or an infrastructure stop (``error``) marks the run
    failed. Limits (browser budget or quota, storage, database) are stops, not failures.
    """
    run_id = client.start_run()
    try:
        report = run_worker_drain(
            client,
            fetcher,
            policy,
            browser=browser,
            llm=llm,
            after_extract=after_extract,
            llm_enqueue=llm_enqueue,
        )
    except DiscoveryMachineApiError as err:
        client.finish_run(run_id, _failed(str(err)))
        raise
    client.finish_run(run_id, _finish_request(report))
    return report.model_copy(update={"run_id": run_id})
