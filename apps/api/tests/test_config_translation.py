"""Translation settings: documented defaults, overrides and validation at load."""

from __future__ import annotations

import pytest
from app.config import Settings
from pydantic import ValidationError


def _settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, **overrides)  # type: ignore[arg-type]


def test_translation_settings_default_to_the_six_target_locales_and_accept_overrides() -> None:
    """settings · the targets default to en tr ru uk pl ro and the recipe version is set; both can be overridden."""
    defaults = _settings()

    assert defaults.translation_target_locale_codes == ("en", "tr", "ru", "uk", "pl", "ro")
    assert defaults.translation_unit_recipe_version
    tuned = _settings(translation_target_locales="tr, pl", translation_unit_recipe_version="v2")
    assert tuned.translation_target_locale_codes == ("tr", "pl")
    assert tuned.translation_unit_recipe_version == "v2"


def test_an_empty_target_list_switches_translation_off() -> None:
    """settings · an empty target list is allowed: it is the rollback (nothing is enqueued)."""
    assert _settings(translation_target_locales="").translation_target_locale_codes == ()


@pytest.mark.parametrize("value", ["de", "en xx", "en,de", "en en"])
def test_a_target_locale_that_is_de_unsupported_or_repeated_fails_at_load(value: str) -> None:
    """settings · a target locale that is de, unsupported or repeated fails at load."""
    with pytest.raises(ValidationError):
        _settings(translation_target_locales=value)


def test_an_empty_recipe_version_fails_at_load() -> None:
    """settings · the unit recipe version cannot be empty, or every hash would collide across recipes."""
    with pytest.raises(ValidationError):
        _settings(translation_unit_recipe_version="")


def test_the_tail_is_off_by_default_and_starts_at_priority_600() -> None:
    """settings · no tail locale is set (D14), and the tail band starts at priority 600."""
    defaults = _settings()

    assert (defaults.translation_tail_locale_codes, defaults.translation_tail_priority_min) == ((), 600)


def test_tail_locales_are_target_locales_and_accept_a_tuned_band() -> None:
    """settings · a tail locale must be a target; the band start can be moved within 0 to 1000."""
    tuned = _settings(
        translation_target_locales="tr pl", translation_tail_locales="tr", translation_tail_priority_min=700
    )

    assert (tuned.translation_tail_locale_codes, tuned.translation_tail_priority_min) == (("tr",), 700)


def test_a_tail_locale_that_is_not_a_target_fails_at_load() -> None:
    """settings · a tail locale outside the targets fails at load, so nothing routes to an untranslated locale."""
    with pytest.raises(ValidationError):
        _settings(translation_target_locales="tr", translation_tail_locales="pl")


@pytest.mark.parametrize("value", [-1, 1001])
def test_a_tail_priority_minimum_outside_zero_to_one_thousand_fails_at_load(value: int) -> None:
    """settings · the tail band starts inside the first-translation band, 0 to 1000."""
    with pytest.raises(ValidationError):
        _settings(translation_tail_priority_min=value)
