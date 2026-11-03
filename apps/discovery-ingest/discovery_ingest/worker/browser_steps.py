"""The steps every browser handler shares: robots, login url, page status, login wall, upload, complete."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

from discovery_ingest.artifacts import ArtifactUpload, StoredArtifact
from discovery_ingest.browser.errors import BrowserRequestError
from discovery_ingest.client import DiscoveryIngestClient, DiscoveryMachineApiError
from discovery_ingest.schemas import ClaimedTask
from discovery_ingest.worker.browser_spend import BrowserSpend
from discovery_ingest.worker.fetcher import PoliteUrlFetcher
from discovery_ingest.worker.login_wall import has_password_input, url_looks_like_login
from discovery_ingest.worker.settle import fail_from_api_error, fail_from_outcome, fail_with
from discovery_ingest.worker.stop import StopDrain

STORAGE_UNAVAILABLE_STATUSES = frozenset({503, 507})
T = TypeVar("T")


class Settled(Exception):
    """A step decided the task's outcome (``completed`` or ``failed``); the later steps are skipped."""

    def __init__(self, outcome: str) -> None:
        """Keep the outcome label the handler returns."""
        super().__init__(outcome)
        self.outcome = outcome


@dataclass(frozen=True, slots=True)
class Job:
    """One claimed task with the collaborators every step needs."""

    task: ClaimedTask
    client: DiscoveryIngestClient
    fetcher: PoliteUrlFetcher


def complete(job: Job, note: str | None) -> str:
    """Complete the task with an optional ``result_note`` and return the outcome label."""
    job.client.tasks.complete(job.task.id, note=note)
    return "completed"


def check_robots(job: Job) -> None:
    """Settle the task as failed when robots.txt disallows the URL (permanent) or cannot be read (retryable)."""
    blocked = job.fetcher.check_robots(job.task.target_url)
    if blocked is not None:
        raise Settled(fail_from_outcome(job.client, job.task.id, blocked))


def skip_login_url(job: Job) -> None:
    """Complete with ``login_wall`` when the task URL already looks like a login URL, before any browser time."""
    if url_looks_like_login(job.task.target_url):
        raise Settled(complete(job, "login_wall"))


def call_browser(job: Job, spend: BrowserSpend, action: Callable[[], T], cost_ms: Callable[[T], int]) -> T:
    """Run a browser call under the budgets; a request error settles the task as failed (retryable per the error)."""
    try:
        return spend.call(action, cost_ms)
    except BrowserRequestError as err:
        raise Settled(fail_with(job.client, job.task.id, str(err), retryable=err.retryable)) from err


def refuse_error_status(job: Job, status: int | None, what: str) -> None:
    """Fail the task when the browser saw an HTTP error (5xx retryable, 4xx permanent); ``what`` names the call."""
    if status is not None and status >= 400:
        raise Settled(fail_with(job.client, job.task.id, f"{what} returned HTTP {status}", retryable=status >= 500))


def is_login_wall(html: str | None, final_url: str | None) -> bool:
    """Whether the DOM asks for a password or the browser ended on a login URL; ``None`` means not seen."""
    return (html is not None and has_password_input(html)) or (
        final_url is not None and url_looks_like_login(final_url)
    )


def store(job: Job, upload: ArtifactUpload) -> StoredArtifact:
    """Upload ``upload`` for the task; a refusal that is a limit raises the exception that stops the drain."""
    try:
        return job.client.artifacts.upload(job.task.id, upload)
    except DiscoveryMachineApiError as err:
        raise refusal_for(job, err) from err


def refusal_for(job: Job, err: DiscoveryMachineApiError) -> Exception:
    """Map a refused machine call to the exception that ends it: a limit stops the drain, anything else settles the task."""
    if err.is_database_limit:
        return err
    if err.status_code in STORAGE_UNAVAILABLE_STATUSES:
        return StopDrain("storage_unavailable", err.detail)
    return Settled(fail_from_api_error(job.client, job.task.id, err))
