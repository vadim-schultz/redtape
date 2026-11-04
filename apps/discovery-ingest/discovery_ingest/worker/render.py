"""Handle render_page tasks: render through the browser port, store the DOM as a snapshot, release on limits."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from discovery_ingest.artifacts import ArtifactRead, ArtifactUpload, StoredArtifact
from discovery_ingest.browser.port import BrowserClient, RenderedPage
from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.schemas import ClaimedTask
from discovery_ingest.worker.browser_spend import BrowserSpend
from discovery_ingest.worker.browser_steps import (
    Job,
    Settled,
    call_browser,
    check_robots,
    complete,
    is_login_wall,
    refuse_error_status,
    skip_login_url,
    store,
)
from discovery_ingest.worker.fetcher import PoliteUrlFetcher

MAX_SNAPSHOT_BYTES = 4 * 1024 * 1024
AfterSnapshot = Callable[[ClaimedTask, ArtifactRead], None]


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

    def __call__(self, task: ClaimedTask, *, client: DiscoveryIngestClient, fetcher: PoliteUrlFetcher) -> str:
        """Render ``task``'s page and return ``completed`` or ``failed``; raise :class:`StopDrain` on a limit."""
        job = Job(task, client, fetcher)
        try:
            self._pipeline(job)
        except Settled as settled:
            return settled.outcome
        return complete(job, None)

    def _pipeline(self, job: Job) -> None:
        check_robots(job)
        skip_login_url(job)
        fetched = self._render(job)
        _verdict(job, fetched.page)
        stored = _upload(job, fetched)
        self._after_snapshot(job.task, stored.artifact)

    def _render(self, job: Job) -> _Fetched:
        page = call_browser(job, self._spend, lambda: self._browser.render(job.task.target_url), lambda p: p.ms_used)
        return _Fetched(page, datetime.now(UTC))


def _verdict(job: Job, page: RenderedPage) -> None:
    refuse_error_status(job, page.http_status, "render")
    note = _skip_note(page)
    if note is not None:
        raise Settled(complete(job, note))


def _skip_note(page: RenderedPage) -> str | None:
    if is_login_wall(page.html, page.final_url):
        return "login_wall"
    return "oversize" if len(page.html.encode()) > MAX_SNAPSHOT_BYTES else None


def _upload(job: Job, fetched: _Fetched) -> StoredArtifact:
    task, page = job.task, fetched.page
    snapshot = ArtifactUpload(
        "html_snapshot", page.html.encode(), "text/html", task.target_url, page.final_url or task.target_url, fetched.at
    )
    return store(job, snapshot)
