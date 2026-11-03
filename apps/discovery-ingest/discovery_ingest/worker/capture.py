"""Handle capture_screenshot tasks: screenshot the page through the browser port and store it as evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from discovery_ingest.artifacts import ArtifactUpload
from discovery_ingest.browser.errors import ScreenshotOversize
from discovery_ingest.browser.port import BrowserClient, ScreenshotImage
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

Shot = ScreenshotImage | ScreenshotOversize
"""What one call returned: an image, or the note that it was over the cap (which still cost browser time)."""


@dataclass(frozen=True, slots=True)
class _Captured:
    shot: Shot
    at: datetime


class CaptureScreenshotHandler:
    """Steps in order: robots, login url, capture, oversize, verdict, upload, complete."""

    def __init__(self, browser: BrowserClient, spend: BrowserSpend) -> None:
        """Wire the browser port and the budgets that every capture spends under."""
        self._browser = browser
        self._spend = spend

    def __call__(self, task: ClaimedTask, *, client: DiscoveryIngestClient, fetcher: PoliteUrlFetcher) -> str:
        """Capture ``task``'s page and return ``completed`` or ``failed``; raise :class:`StopDrain` on a limit."""
        job = Job(task, client, fetcher)
        try:
            self._pipeline(job)
        except Settled as settled:
            return settled.outcome
        return complete(job, None)

    def _pipeline(self, job: Job) -> None:
        check_robots(job)
        skip_login_url(job)
        captured = self._capture(job)
        image = _image_or_oversize(job, captured.shot)
        _verdict(job, image)
        store(job, _evidence(job.task, image, captured.at))

    def _capture(self, job: Job) -> _Captured:
        shot = call_browser(job, self._spend, lambda: _shoot(self._browser, job.task.target_url), lambda s: s.ms_used)
        return _Captured(shot, datetime.now(UTC))


def _shoot(browser: BrowserClient, url: str) -> Shot:
    """Return the screenshot, or the oversize signal as a value so its browser time is booked like any other call."""
    try:
        return browser.screenshot(url)
    except ScreenshotOversize as oversize:
        return oversize


def _image_or_oversize(job: Job, shot: Shot) -> ScreenshotImage:
    if isinstance(shot, ScreenshotOversize):
        raise Settled(complete(job, "oversize"))
    return shot


def _verdict(job: Job, image: ScreenshotImage) -> None:
    refuse_error_status(job, image.http_status, "screenshot")
    if is_login_wall(image.html, image.final_url):
        raise Settled(complete(job, "login_wall"))


def _evidence(task: ClaimedTask, image: ScreenshotImage, at: datetime) -> ArtifactUpload:
    final = image.final_url or task.target_url
    return ArtifactUpload("screenshot", image.data, image.content_type, task.target_url, final, at)
