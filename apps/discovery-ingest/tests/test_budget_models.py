"""The ingest budget literal accepts every resource the API ledger guards."""

from __future__ import annotations

import pytest
from discovery_ingest.budget_models import BUDGET_RESOURCES, BudgetRow
from pydantic import ValidationError


def _row(resource: str) -> dict[str, object]:
    return {
        "resource": resource,
        "period": "2026-11",
        "cap": 1_900_000,
        "used": 0,
        "remaining": 1_900_000,
        "exhausted": False,
    }


def test_the_budget_row_literal_accepts_azure_translator_chars() -> None:
    row = BudgetRow.model_validate(_row("azure_translator_chars"))

    assert row.resource == "azure_translator_chars"
    assert "azure_translator_chars" in BUDGET_RESOURCES


def test_the_budget_row_literal_still_refuses_an_unknown_resource() -> None:
    with pytest.raises(ValidationError):
        BudgetRow.model_validate(_row("bananas"))
