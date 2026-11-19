"""Fused render: one /snapshot call stores the HTML and the screenshot; the image is stored best effort (chapter 8)."""

from __future__ import annotations

import sys
from datetime import UTC, datetime

import httpx

from discovery_ingest.browser.errors import ScreenshotOversize, ScreenshotUnreadable
from discovery_ingest.browser.port import BrowserClient, RenderedPage, ScreenshotImage
from discovery_ingest.client import DiscoveryMachineApiError
from discovery_ingest.worker.browser_steps import STORAGE_UNAVAILABLE_STATUSES, Job, Settled, call_browser, refusal_for
from discovery_ingest.worker.capture import screenshot_evidence
from discovery_ingest.worker.render import Fetched, RenderPageHandler
from discovery_ingest.worker.settle import fail_with

SHOT_OVERSIZE = "oversize_screenshot"
SHOT_FAILED = "screenshot_failed"
FusedShot = ScreenshotImage | ScreenshotOversize | ScreenshotUnreadable
"""What one fused call returned: an image, or the DOM of a call whose image could not be kept."""


class FusedRenderPageHandler(RenderPageHandler):
    """Steps in order: robots, login url, one /snapshot call, verdict, upload HTML, hook, upload screenshot, complete.

    The HTML is stored before the hook, so the hook sees the snapshot it reads. The screenshot is stored after the
    hook and is best effort: a failure or an oversize image completes the task with a note and keeps the HTML.
    """

    def _render(self, job: Job) -> Fetched:
        shot = call_browser(job, self._spend, lambda: _snapshot(self._browser, job.task.target_url), _cost)
        return _fetched(job, shot)

    def _after_html(self, job: Job, fetched: Fetched) -> str | None:
        if fetched.shot is None:
            return fetched.shot_note
        return _store_image(job, fetched.shot, fetched.at)


def _snapshot(browser: BrowserClient, url: str) -> FusedShot:
    """Return the fused image, or an oversize or unreadable call as a value so its DOM and its browser time are kept."""
    try:
        return browser.screenshot(url, consent_click=False)
    except (ScreenshotOversize, ScreenshotUnreadable) as kept:
        return kept


def _cost(shot: FusedShot) -> int:
    return shot.ms_used or 0


def _fetched(job: Job, shot: FusedShot) -> Fetched:
    now = datetime.now(UTC)
    if isinstance(shot, ScreenshotImage):
        return Fetched(_page_or_fail(job, _image_page(shot)), now, shot=shot)
    note = SHOT_OVERSIZE if isinstance(shot, ScreenshotOversize) else SHOT_FAILED
    return Fetched(_page_or_fail(job, shot.page), now, shot_note=note)


def _image_page(shot: ScreenshotImage) -> RenderedPage | None:
    if shot.html is None:
        return None
    return RenderedPage(shot.html, shot.ms_used, shot.http_status, shot.final_url)


def _page_or_fail(job: Job, page: RenderedPage | None) -> RenderedPage:
    """Return the page to store, or fail the task permanently when Cloudflare sent no DOM to store."""
    if page is None:
        raise Settled(fail_with(job.client, job.task.id, "Cloudflare returned no HTML", retryable=False))
    return page


def _store_image(job: Job, shot: ScreenshotImage, at: datetime) -> str | None:
    """Upload the screenshot best effort: ``None`` when it is stored, otherwise the note for the completion."""
    try:
        job.client.artifacts.upload(job.task.id, screenshot_evidence(job.task, shot, at))
    except DiscoveryMachineApiError as err:
        return _image_refused(job, err)
    except httpx.HTTPError as err:
        return _image_failed(job, err)
    return None


def _image_refused(job: Job, err: DiscoveryMachineApiError) -> str:
    if _stops_drain(err):
        raise refusal_for(job, err) from err
    return _image_failed(job, err)


def _stops_drain(err: DiscoveryMachineApiError) -> bool:
    """Whether a refusal is a limit or unavailable storage, which ends the drain rather than one screenshot."""
    return err.is_database_limit or err.status_code in STORAGE_UNAVAILABLE_STATUSES


def _image_failed(job: Job, err: Exception) -> str:
    print(f"screenshot upload failed for {job.task.target_url}: {err}", file=sys.stderr)
    return SHOT_FAILED
