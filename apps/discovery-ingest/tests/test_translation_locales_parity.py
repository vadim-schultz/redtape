"""Parity · the ingest target locales equal the API's translation target defaults and embedding_locales minus de (chapter 16).

The API is another application, so its defaults are read from its settings source, not imported.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from discovery_ingest.translation.locale_codes import DEFAULT_TARGET_LOCALES

API_CONFIG = Path(__file__).resolve().parents[3] / "apps" / "api" / "app" / "config.py"
SOURCE_LOCALE = "de"


def _default_of(call: ast.expr) -> str:
    """Return the string value of the ``default=`` keyword of a ``Field(...)`` call."""
    assert isinstance(call, ast.Call)
    (default,) = [keyword.value for keyword in call.keywords if keyword.arg == "default"]
    assert isinstance(default, ast.Constant) and isinstance(default.value, str)
    return default.value


def _api_default(field: str) -> str:
    """Return the default of the API ``Settings`` field ``field``, read from the source."""
    for node in ast.walk(ast.parse(API_CONFIG.read_text(encoding="utf-8"))):
        if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", None) == field:
            return _default_of(node.value)
    raise AssertionError(f"apps/api/app/config.py has no field {field}")


def _codes(value: str) -> tuple[str, ...]:
    """Split a locale list the way the API does: spaces or commas."""
    return tuple(value.replace(",", " ").split())


def parity_problems(ingest: tuple[str, ...], api_targets: str, embedding: str) -> list[str]:
    """Return one message for each way the lists disagree; an empty list means parity holds."""
    targets = _codes(api_targets)
    expected = tuple(code for code in _codes(embedding) if code != SOURCE_LOCALE)
    problems = []
    if ingest != targets:
        problems.append(f"ingest DEFAULT_TARGET_LOCALES {ingest} differs from the API default {targets}")
    if targets != expected:
        problems.append(f"the API default {targets} differs from embedding_locales minus de {expected}")
    return problems


def test_the_ingest_targets_equal_the_api_defaults_and_the_embedding_set_minus_de() -> None:
    """Parity · ingest DEFAULT_TARGET_LOCALES equals the API default targets and embedding_locales minus de."""
    problems = parity_problems(
        DEFAULT_TARGET_LOCALES, _api_default("translation_target_locales"), _api_default("embedding_locales")
    )

    assert problems == []


@pytest.mark.parametrize(
    ("ingest", "api_targets", "embedding"),
    [
        (("en", "tr", "ru", "uk", "pl"), "en tr ru uk pl ro", "de en tr ru uk pl ro"),
        (DEFAULT_TARGET_LOCALES, "en tr ru uk pl ro nb", "de en tr ru uk pl ro"),
        (DEFAULT_TARGET_LOCALES, "en tr ru uk pl ro", "de en tr ru uk pl ro nb"),
    ],
)
def test_drift_between_the_ingest_and_api_target_lists_fails_the_parity_check(
    ingest: tuple[str, ...], api_targets: str, embedding: str
) -> None:
    """Parity · a target list that drifts from the other one, or from the embedding set, is reported."""
    assert parity_problems(ingest, api_targets, embedding) != []
