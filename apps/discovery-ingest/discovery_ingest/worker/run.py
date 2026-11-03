"""Record a worker drain as an explicit run through the machine API."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

import httpx

from discovery_ingest.browser.port import BrowserClient
from discovery_ingest.client import DiscoveryIngestClient, DiscoveryMachineApiError
from discovery_ingest.schemas import DrainReport, RunFinishRequest
from discovery_ingest.worker.drain import run_worker_drain
from discovery_ingest.worker.fetcher import PoliteUrlFetcher
from discovery_ingest.worker.llm_enqueue import LlmEnqueuer
from discovery_ingest.worker.llm_extract import AfterExtract, no_after_extract
from discovery_ingest.worker.llm_runtime import LlmResources
from discovery_ingest.worker.policy import DrainPolicy

logger = logging.getLogger(__name__)

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


def _detail_for(err: BaseException) -> str:
    """Describe ``err`` for ``error_detail``: ``str(err)`` for an API error, else ``Type: message``."""
    if isinstance(err, KeyboardInterrupt):
        return "interrupted"
    if isinstance(err, DiscoveryMachineApiError):
        return str(err)
    return f"{type(err).__name__}: {err}"


class RecordedRun:
    """A run open on the machine API, closed by exactly one call to :meth:`finish`."""

    def __init__(self, client: DiscoveryIngestClient, run_id: UUID) -> None:
        """Keep the client and the id of the run :func:`recorded_run` already started."""
        self._client = client
        self.run_id = run_id
        self.finished = False

    def finish(self, body: RunFinishRequest) -> None:
        """Close the run with ``body``; mark it attempted before the call so a failed finish is never repeated."""
        self.finished = True
        self._client.runs.finish(self.run_id, body)


@contextmanager
def recorded_run(client: DiscoveryIngestClient) -> Iterator[RecordedRun]:
    """Open a run and guarantee that it is finished, as failed when the body leaves without finishing it."""
    run = RecordedRun(client, client.runs.start())
    try:
        yield run
    except BaseException as err:
        if not run.finished:
            _finish_quietly(run, _failed(_detail_for(err)))
        raise
    else:
        if not run.finished:
            run.finish(_failed("the drain returned without finishing the run"))


def _finish_quietly(run: RecordedRun, body: RunFinishRequest) -> None:
    """Attempt one failure finish; a failure of this call itself is only logged, never raised over the caller's."""
    try:
        run.finish(body)
    except (DiscoveryMachineApiError, httpx.HTTPError) as err:
        logger.warning("could not finish run %s as failed: %s", run.run_id, err)


def run_recorded_drain(
    client: DiscoveryIngestClient,
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
    with recorded_run(client) as run:
        report = run_worker_drain(
            client,
            fetcher,
            policy,
            browser=browser,
            llm=llm,
            after_extract=after_extract,
            llm_enqueue=llm_enqueue,
        )
        run.finish(_finish_request(report))
    return report.model_copy(update={"run_id": run.run_id})
