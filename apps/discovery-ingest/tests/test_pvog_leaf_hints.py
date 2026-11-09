"""PVOG leaf hints · one value read from the payload once, equal to the five per-field lookups it replaces."""

from __future__ import annotations

import pytest
from discovery_ingest.harvest.pvog import LeafHints

from crosswalk_fakes import CROSSWALK


def _expected(code: str | None) -> LeafHints:
    """The source-only values available without a complete PVOG path."""
    if code is None:
        return LeafHints(None, None, None, None, None)
    return LeafHints(None, None, code, None, None)


@pytest.mark.parametrize(
    "code",
    [
        "1180100",  # clean situation mapping
        "1040300",  # ambiguous, bundled situation codes
        "1020200",  # domain hint only
        "1170100",  # in neither table
        None,  # no stashed code at all
    ],
)
def test_leaf_hints_from_payload_keeps_leaf_without_a_complete_pvog_path(code: str | None) -> None:
    """LeafHints · a leaf remains provenance when no complete PVOG path is available."""
    payload: dict[str, object] = {"languageCode": "de"}
    if code is not None:
        payload["_personal_matter_code"] = code

    assert LeafHints.from_payload(payload, CROSSWALK) == _expected(code)


def test_leaf_hints_keeps_an_empty_code_as_the_leaf_code_without_any_mapping() -> None:
    """LeafHints · an empty stashed code remains source-only."""
    hints = LeafHints.from_payload({"_personal_matter_code": ""}, CROSSWALK)

    assert hints.leaf_code == ""
    assert hints.category_codes is None


def test_leaf_hints_ignores_a_non_string_code() -> None:
    """LeafHints · a stashed value that is not a string is no code at all."""
    assert LeafHints.from_payload({"_personal_matter_code": 1180100}, CROSSWALK) == LeafHints(
        None, None, None, None, None
    )
