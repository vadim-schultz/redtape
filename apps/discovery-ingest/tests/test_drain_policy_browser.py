"""DrainPolicy knows which kinds spend browser time and requires a budget for them (chapter 15, Loop C)."""

from __future__ import annotations

import pytest
from discovery_ingest.schemas import BROWSER_TASK_KINDS, WORKER_DEFAULT_TASK_KINDS
from discovery_ingest.worker.policy import DrainPolicy


def test_default_kinds_exclude_render_page_and_capture_screenshot() -> None:
    """policy · the default worker kinds never include a browser kind."""
    assert set(BROWSER_TASK_KINDS) == {"render_page", "capture_screenshot"}
    assert not set(WORKER_DEFAULT_TASK_KINDS) & set(BROWSER_TASK_KINDS)
    assert DrainPolicy().drains_browser_kinds is False


def test_a_browser_kind_needs_a_positive_browser_budget() -> None:
    """policy · render_page or capture_screenshot without a budget, or a budget of zero, is rejected."""
    for kinds in (("render_page",), ("fetch_url", "capture_screenshot")):
        with pytest.raises(ValueError, match="browser_budget_seconds is required"):
            DrainPolicy(kinds=kinds)
    with pytest.raises(ValueError, match="positive"):
        DrainPolicy(kinds=("render_page",), browser_budget_seconds=0)

    assert DrainPolicy(kinds=("render_page",), browser_budget_seconds=480).drains_browser_kinds is True
    assert DrainPolicy(browser_budget_seconds=480).drains_browser_kinds is False
