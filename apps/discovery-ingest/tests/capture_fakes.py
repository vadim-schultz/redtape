"""Fakes for the capture worker tests: a scripted screenshot browser and a one-batch drain without the registry."""

from __future__ import annotations

from typing import NamedTuple

import pytest
from discovery_ingest.browser.budget import BrowserBudget
from discovery_ingest.browser.errors import BrowserError
from discovery_ingest.browser.port import RenderedPage, ScreenshotImage
from discovery_ingest.budget import BudgetGuard
from discovery_ingest.worker.batch import BatchResult, DrainContext, run_batch
from discovery_ingest.worker.browser_spend import BrowserSpend
from discovery_ingest.worker.capture import CaptureScreenshotHandler
from discovery_ingest.worker.policy import DrainPolicy
from discovery_ingest.worker.tally import Tally

from render_fakes import FakeApi, robots_fetcher

JPEG = b"\xff\xd8\xff" + b"j" * 64


class FakeCamera:
    """A scripted browser: each ``screenshot`` returns the next image or raises the next error; calls are recorded."""

    def __init__(self, *outcomes: ScreenshotImage | BrowserError) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[str] = []

    def render(self, url: str) -> RenderedPage:
        """Not used by chapter 19."""
        raise NotImplementedError

    def screenshot(self, url: str) -> ScreenshotImage:
        """Return or raise the next scripted outcome."""
        self.calls.append(url)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BrowserError):
            raise outcome
        return outcome


def shot(
    html: str | None = "<html><body>evidence</body></html>",
    *,
    ms: int = 2000,
    status: int | None = 200,
    final_url: str | None = "https://portal.example/final",
    data: bytes = JPEG,
) -> ScreenshotImage:
    """Return a JPEG screenshot costing ``ms`` browser milliseconds."""
    return ScreenshotImage(data, "image/jpeg", ms, html, status, final_url)


class Drained(NamedTuple):
    """What one batch left behind: the counters, the batch result and the browser budget."""

    tally: Tally
    batch: BatchResult
    spend: BrowserSpend


def drain_captures(
    monkeypatch: pytest.MonkeyPatch,
    api: FakeApi,
    camera: FakeCamera,
    *,
    budget_seconds: float = 480.0,
    robots: str | None = None,
) -> Drained:
    """Claim one batch of ``capture_screenshot`` tasks and settle it with the handler under test."""
    client = api.client(monkeypatch)
    spend = BrowserSpend(BrowserBudget(budget_seconds), BudgetGuard(client))
    policy = DrainPolicy(max_tasks=5, kinds=("capture_screenshot",), browser_budget_seconds=budget_seconds)
    handlers = {"capture_screenshot": CaptureScreenshotHandler(camera, spend)}
    ctx = DrainContext(client, robots_fetcher(robots), policy, handlers)
    tally = Tally()
    return Drained(tally, run_batch(ctx, tally), spend)
