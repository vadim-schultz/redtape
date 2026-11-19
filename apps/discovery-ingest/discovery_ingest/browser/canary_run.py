"""Run the fused-render canary against a browser: stable pages only, /content against the fused /snapshot (chapter 8)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol

from discovery_ingest.browser.canary import CanaryVerdict, PageCompare, compare_page, judge, page_hash
from discovery_ingest.browser.errors import (
    BrowserAuthError,
    BrowserQuotaExceeded,
    BrowserRequestError,
    ScreenshotOversize,
)
from discovery_ingest.browser.port import RenderedPage, ScreenshotImage


class CanaryBrowser(Protocol):
    """The two calls the canary compares: the /content render and the fused /snapshot screenshot."""

    def render(self, url: str) -> RenderedPage:
        """Return the rendered DOM of ``url``."""
        ...

    def screenshot(self, url: str, *, consent_click: bool = True) -> ScreenshotImage:
        """Return the image and DOM of ``url`` from one /snapshot call."""
        ...


@dataclass(frozen=True, slots=True)
class CanaryRun:
    """One canary run: the measured pages, the skipped URLs, the browser time spent, the stop and the verdict."""

    required: int
    pages: tuple[PageCompare, ...]
    skipped: tuple[str, ...]
    spent_ms: int
    stopped: str | None
    verdict: CanaryVerdict


@dataclass(slots=True)
class _Walk:
    """The running tally of one walk over the candidate URLs."""

    pages: list[PageCompare] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    spent_ms: int = 0
    stopped: str | None = None


def run_canary(browser: CanaryBrowser, urls: Sequence[str], *, required: int, max_ms: int) -> CanaryRun:
    """Measure stable pages in ``urls`` order until ``required`` are found, ``max_ms`` is spent or Cloudflare refuses."""
    walk = _Walk()
    for url in urls:
        if len(walk.pages) >= required:
            break
        if walk.spent_ms >= max_ms:
            walk.stopped = "browser time cap reached"
            break
        if not _walk_one(browser, url, walk):
            break
    verdict = judge(walk.pages, required=required)
    return CanaryRun(required, tuple(walk.pages), tuple(walk.skipped), walk.spent_ms, walk.stopped, verdict)


def _walk_one(browser: CanaryBrowser, url: str, walk: _Walk) -> bool:
    """Measure ``url`` into ``walk``; return false when Cloudflare refused and the walk must stop."""
    try:
        _measure(browser, url, walk)
    except (BrowserQuotaExceeded, BrowserAuthError) as err:
        walk.stopped = str(err)
        return False
    except BrowserRequestError as err:
        walk.skipped.append(url)
        walk.spent_ms += err.ms_used or 0
    return True


def _measure(browser: CanaryBrowser, url: str, walk: _Walk) -> None:
    first, second = browser.render(url), browser.render(url)
    walk.spent_ms += first.ms_used + second.ms_used
    if page_hash(first.html, url) != page_hash(second.html, url):
        walk.skipped.append(url)
        return
    fused_html = _fused_html(browser, url, walk)
    if fused_html is None:
        walk.skipped.append(url)
        return
    walk.pages.append(compare_page(first.html, fused_html, url))


def _fused_html(browser: CanaryBrowser, url: str, walk: _Walk) -> str | None:
    """Return the DOM of the fused call with the accept script off; an oversize image still keeps its DOM."""
    try:
        shot = browser.screenshot(url, consent_click=False)
    except ScreenshotOversize as oversize:
        walk.spent_ms += oversize.ms_used
        return None if oversize.page is None else oversize.page.html
    walk.spent_ms += shot.ms_used
    return shot.html


def canary_lines(run: CanaryRun) -> list[str]:
    """Return the table lines of a run: the verdict, one line per measured page, skips, the stop and the cost."""
    skipped = [f"skipped (unstable or refused): {url}" for url in run.skipped]
    stop = [f"stopped: {run.stopped}"] if run.stopped else []
    return [_verdict_line(run), *(_row(page) for page in run.pages), *skipped, *stop, _cost_line(run)]


def _verdict_line(run: CanaryRun) -> str:
    verdict = run.verdict
    return f"canary pages={verdict.pages} required={run.required} identical={verdict.identical} passed={verdict.passed}"


def _cost_line(run: CanaryRun) -> str:
    per_page = run.spent_ms / 1000 / max(run.verdict.pages, 1)
    return f"browser seconds={run.spent_ms / 1000:.1f} per_page={per_page:.1f}"


def _row(page: PageCompare) -> str:
    return (
        f"  identical={page.identical} text_loss={page.text_loss:.1%} "
        f"blocks={page.content_blocks}->{page.fused_blocks} links={page.content_links}->{page.fused_links}"
    )
