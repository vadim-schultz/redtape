"""The table lines of one fused-render canary run: the verdict, each measured page, the skips, the stop and the cost."""

from __future__ import annotations

from discovery_ingest.browser.canary import PageCompare
from discovery_ingest.browser.canary_run import CanaryRun


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
