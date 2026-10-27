"""Handle render_page tasks: render through the browser port, store the DOM as a snapshot, release on limits."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from discovery_ingest.api_client import DiscoveryMachineApiError, DiscoveryMachineClient
from discovery_ingest.artifacts import ArtifactRead, ArtifactUpload, StoredArtifact
from discovery_ingest.browser.errors import BrowserRequestError
from discovery_ingest.browser.port import BrowserClient, RenderedPage
from discovery_ingest.schemas import ClaimedTask
from discovery_ingest.worker.browser_spend import BrowserSpend
from discovery_ingest.worker.fetcher import PoliteUrlFetcher
from discovery_ingest.worker.login_wall import has_password_input, url_looks_like_login
from discovery_ingest.worker.settle import fail_from_api_error, fail_from_outcome, fail_with
from discovery_ingest.worker.stop import StopDrain

MAX_SNAPSHOT_BYTES = 4 * 1024 * 1024
STORAGE_UNAVAILABLE_STATUSES = frozenset({503, 507})
AfterSnapshot = Callable[[ClaimedTask, ArtifactRead], None]


def ignore_snapshot(task: ClaimedTask, artifact: ArtifactRead) -> None:
    """Default hook: nothing follows a snapshot until an extractor is registered (chapter 17)."""


class _Settled(Exception):
    """A step decided the task's outcome (``completed`` or ``failed``); the later steps are skipped."""

    def __init__(self, outcome: str) -> None:
        super().__init__(outcome)
        self.outcome = outcome


@dataclass(frozen=True, slots=True)
class _Job:
    task: ClaimedTask
    client: DiscoveryMachineClient
    fetcher: PoliteUrlFetcher


@dataclass(frozen=True, slots=True)
class _Fetched:
    page: RenderedPage
    at: datetime


class RenderPageHandler:
    """Steps in order: robots, login url, render, verdict, upload, hook, complete."""

    def __init__(self, browser: BrowserClient, spend: BrowserSpend, after_snapshot: AfterSnapshot) -> None:
        """Wire the browser port, the budgets and the hook that runs after a snapshot is stored."""
        self._browser = browser
        self._spend = spend
        self._after_snapshot = after_snapshot

    def __call__(self, task: ClaimedTask, *, client: DiscoveryMachineClient, fetcher: PoliteUrlFetcher) -> str:
        """Render ``task``'s page and return ``completed`` or ``failed``; raise :class:`StopDrain` on a limit."""
        job = _Job(task, client, fetcher)
        try:
            self._pipeline(job)
        except _Settled as settled:
            return settled.outcome
        return _complete(job, None)

    def _pipeline(self, job: _Job) -> None:
        _robots(job)
        _login_url(job)
        fetched = self._render(job)
        _verdict(job, fetched.page)
        stored = _upload(job, fetched)
        self._after_snapshot(job.task, stored.artifact)

    def _render(self, job: _Job) -> _Fetched:
        try:
            page = self._spend.call(lambda: self._browser.render(job.task.target_url), lambda page: page.ms_used)
        except BrowserRequestError as err:
            raise _Settled(fail_with(job.client, job.task.id, str(err), retryable=err.retryable)) from err
        return _Fetched(page, datetime.now(UTC))


def _complete(job: _Job, note: str | None) -> str:
    job.client.complete_task(job.task.id, note=note)
    return "completed"


def _robots(job: _Job) -> None:
    blocked = job.fetcher.check_robots(job.task.target_url)
    if blocked is not None:
        raise _Settled(fail_from_outcome(job.client, job.task.id, blocked))


def _login_url(job: _Job) -> None:
    if url_looks_like_login(job.task.target_url):
        raise _Settled(_complete(job, "login_wall"))


def _verdict(job: _Job, page: RenderedPage) -> None:
    status = page.http_status
    if status is not None and status >= 400:
        raise _Settled(fail_with(job.client, job.task.id, f"render returned HTTP {status}", retryable=status >= 500))
    note = _skip_note(page)
    if note is not None:
        raise _Settled(_complete(job, note))


def _skip_note(page: RenderedPage) -> str | None:
    if has_password_input(page.html) or (page.final_url and url_looks_like_login(page.final_url)):
        return "login_wall"
    return "oversize" if len(page.html.encode()) > MAX_SNAPSHOT_BYTES else None


def _upload(job: _Job, fetched: _Fetched) -> StoredArtifact:
    task, page = job.task, fetched.page
    snapshot = ArtifactUpload(
        "html_snapshot", page.html.encode(), "text/html", task.target_url, page.final_url or task.target_url, fetched.at
    )
    try:
        return job.client.upload_artifact(task.id, snapshot)
    except DiscoveryMachineApiError as err:
        raise _upload_refused(job, err) from err


def _upload_refused(job: _Job, err: DiscoveryMachineApiError) -> Exception:
    """Map a refused upload to the exception that ends it: a limit stops the drain, anything else settles the task."""
    if err.is_database_limit:
        return err
    if err.status_code in STORAGE_UNAVAILABLE_STATUSES:
        return StopDrain("storage_unavailable", err.detail)
    return _Settled(fail_from_api_error(job.client, job.task.id, err))
