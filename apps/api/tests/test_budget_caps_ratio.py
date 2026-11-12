"""The free-tier caps sit at 95 percent of each provider allowance (extraction chapter E11)."""

from __future__ import annotations

import pytest
from app.config import Settings

# Provider free allowances, written down once. The runtime never reads this table: it exists so that a
# changed allowance is a one-line edit here, with the failing tests below pointing at the stale cap.
ALLOWANCES: dict[str, int] = {
    "object_store_max_bytes": 10_000_000_000,  # R2 storage, 10 GB-month
    "budget_r2_class_a_monthly": 1_000_000,  # R2 Class A operations a month
    "budget_r2_class_b_monthly": 10_000_000,  # R2 Class B operations a month
    "budget_browser_seconds_daily": 600,  # Browser Run seconds a day
    "budget_neurons_daily": 10_000,  # Workers AI neurons a day
    "budget_azure_translator_chars_monthly": 2_000_000,  # Azure AI Translator F0 characters a month
    "db_soft_limit_bytes": 500_000_000,  # Supabase read-only above 500 MB
}


def _cap(name: str) -> int:
    value = getattr(Settings(_env_file=None), name)
    assert isinstance(value, int)
    return value


@pytest.mark.parametrize("name", sorted(ALLOWANCES))
def test_every_cap_is_at_most_95_percent_of_its_allowance(name: str) -> None:
    assert _cap(name) <= 0.95 * ALLOWANCES[name], f"{name} must leave 5 percent of the allowance free"


@pytest.mark.parametrize("name", sorted(ALLOWANCES))
def test_no_cap_falls_back_below_90_percent_of_its_allowance(name: str) -> None:
    assert _cap(name) >= 0.90 * ALLOWANCES[name], f"{name} dropped back to a conservative value"


def test_the_actions_minutes_budget_stays_a_repository_share_of_the_account_pool() -> None:
    settings = Settings(_env_file=None)

    assert (settings.budget_actions_minutes_monthly, settings.actions_ci_reserve_minutes) == (2_000, 1_000), (
        "the free Actions minutes are shared by every repository on the account; "
        "2,000 is this repository's assumed share, split evenly between scheduled drains and CI"
    )


def test_the_azure_translator_cap_is_read_from_its_environment_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BUDGET_AZURE_TRANSLATOR_CHARS_MONTHLY", "1234")

    assert Settings(_env_file=None).budget_azure_translator_chars_monthly == 1234


def test_an_environment_override_still_wins_over_the_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BUDGET_NEURONS_DAILY", "8000")
    monkeypatch.setenv("OBJECT_STORE_MAX_BYTES", "8589934592")

    settings = Settings(_env_file=None)

    assert (settings.budget_neurons_daily, settings.object_store_max_bytes) == (8_000, 8 * 1024**3)
