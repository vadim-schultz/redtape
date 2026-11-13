"""Record a drain as an explicit run through the machine API: the worker drain, and the embed, translate and snapshot drains."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from uuid import UUID

import httpx

from discovery_ingest.client import DiscoveryIngestClient, DiscoveryMachineApiError
from discovery_ingest.schemas import DrainReport, RunFinishRequest, RunStage
from discovery_ingest.worker.drain import run_worker_drain
from discovery_ingest.worker.drain_deps import DrainDeps
from discovery_ingest.worker.policy import DrainPolicy

logger = logging.getLogger(__name__)

_MAX_ERROR_DETAIL = 1000


def _spend(report: DrainReport) -> dict[str, float]:
    """Return the browser seconds, neurons and Azure characters the drain used, by the ledger's resource names."""
    return {
        "browser_seconds": report.browser_seconds_used,
        "neurons": report.neurons_used,
        "azure_translator_chars": float(report.characters_used),
    }


def _succeeded(report: DrainReport) -> RunFinishRequest:
    return RunFinishRequest(
        status="succeeded",
        claimed_count=report.claimed,
        completed_count=report.completed,
        failed_count=report.failed,
        skipped_count=report.skipped,
        remaining_count=report.remaining,
        stop_reason=report.stop_reason,
        spend=_spend(report),
    )


def _failed(detail: str, spend: dict[str, float] | None = None) -> RunFinishRequest:
    return RunFinishRequest(
        status="failed",
        claimed_count=0,
        completed_count=0,
        failed_count=0,
        skipped_count=0,
        stop_reason="error",
        error_detail=detail[:_MAX_ERROR_DETAIL],
        spend=spend,
    )


def _finish_request(report: DrainReport) -> RunFinishRequest:
    """Map a drain report to its run-finish request; an infrastructure error (``error``) fails the run, keeping its spend."""
    if report.succeeded:
        return _succeeded(report)
    return _failed(report.error or "the drain stopped on an error", _spend(report))


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
def recorded_run(client: DiscoveryIngestClient, stage: RunStage = "worker_drain") -> Iterator[RecordedRun]:
    """Open a run for ``stage`` and guarantee that it is finished, as failed when the body leaves without finishing it."""
    run = RecordedRun(client, client.runs.start(stage=stage))
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


def run_recorded(client: DiscoveryIngestClient, stage: RunStage, drain: Callable[[], DrainReport]) -> DrainReport:
    """Run ``drain`` between a run start for ``stage`` and a run finish, and return its report.

    Individual task failures stay in the report; an API failure or an infrastructure stop (``error``) marks the run
    failed. Limits (browser budget or quota, storage, database) are stops, not failures. An exception from ``drain``
    (a refused setup included) closes the run as failed and is raised again.
    """
    with recorded_run(client, stage) as run:
        report = drain()
        run.finish(_finish_request(report))
    return report.model_copy(update={"run_id": run.run_id})


def run_recorded_drain(deps: DrainDeps, policy: DrainPolicy) -> DrainReport:
    """Drain bounded batches of the worker kinds as a ``worker_drain`` run."""
    return run_recorded(deps.client, "worker_drain", lambda: run_worker_drain(deps, policy))
