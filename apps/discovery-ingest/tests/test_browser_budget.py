"""The run's browser-time budget: summed milliseconds against a limit in seconds (chapter 15, Loop A)."""

from __future__ import annotations

import pytest
from discovery_ingest.browser.budget import BrowserBudget


def test_budget_reports_exhausted_once_the_summed_ms_used_passes_the_limit() -> None:
    """budget · exhausted when the sum reaches the limit, not before."""
    budget = BrowserBudget(10.0)

    budget.spend(4_000)
    assert (budget.exhausted, budget.used_seconds) == (False, 4.0)

    budget.spend(6_000)
    assert (budget.exhausted, budget.used_seconds) == (True, 10.0)


def test_budget_rejects_a_negative_spend_and_a_non_positive_limit() -> None:
    """budget · negative spend and a zero or negative limit are programming errors."""
    with pytest.raises(ValueError, match="limit"):
        BrowserBudget(0)
    budget = BrowserBudget(5.0)
    with pytest.raises(ValueError, match="non-negative"):
        budget.spend(-1)
    assert budget.used_seconds == 0.0
