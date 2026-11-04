"""PageBudget · the page and record caps shared by the crawl clients."""

from __future__ import annotations

import pytest
from discovery_ingest.page_budget import PageBudget


def test_page_budget_zero_pages_is_exhausted() -> None:
    """PageBudget · a zero page cap is exhausted before any fetch."""
    assert PageBudget(max_pages=0).exhausted


def test_page_budget_one_page_is_exhausted_after_one_spend() -> None:
    """PageBudget · a page cap of one allows exactly one fetch."""
    budget = PageBudget(max_pages=1)
    assert not budget.exhausted
    budget.spend_page()
    assert budget.exhausted


def test_page_budget_two_pages_allows_two_spends() -> None:
    """PageBudget · a page cap of two allows two fetches."""
    budget = PageBudget(max_pages=2)
    budget.spend_page()
    assert not budget.exhausted
    budget.spend_page()
    assert budget.exhausted


def test_page_budget_without_a_cap_is_never_exhausted_by_pages() -> None:
    """PageBudget · ``max_pages=None`` never runs out of pages."""
    budget = PageBudget(max_pages=None)
    for _ in range(1000):
        budget.spend_page()
    assert not budget.exhausted


def test_page_budget_admit_keeps_everything_without_a_record_cap() -> None:
    """PageBudget · with no record cap every record of the page is kept."""
    budget = PageBudget(max_pages=None)
    assert budget.admit(["a", "b", "c"]) == ["a", "b", "c"]


def test_page_budget_admit_trims_to_remaining_records() -> None:
    """PageBudget · a record cap trims the page mid-way and then reports exhaustion."""
    budget = PageBudget(max_pages=None, max_records=3)
    assert budget.admit(["a", "b"]) == ["a", "b"]
    assert not budget.exhausted
    assert budget.admit(["c", "d", "e"]) == ["c"]
    assert budget.exhausted


def test_page_budget_admit_returns_nothing_once_the_record_cap_is_reached() -> None:
    """PageBudget · admitting after the record cap keeps nothing."""
    budget = PageBudget(max_pages=None, max_records=1)
    budget.admit(["a"])
    assert budget.exhausted
    assert budget.admit(["b"]) == []


def test_page_budget_record_cap_exhausts_even_with_pages_left() -> None:
    """PageBudget · the record cap alone makes the budget exhausted."""
    budget = PageBudget(max_pages=10, max_records=2)
    budget.spend_page()
    budget.admit(["a", "b"])
    assert budget.exhausted


@pytest.mark.parametrize("max_pages", [0, -1])
def test_page_budget_non_positive_pages_is_exhausted(max_pages: int) -> None:
    """PageBudget · any page cap below one is exhausted at once, as the crawl loops expect."""
    assert PageBudget(max_pages=max_pages).exhausted
