"""PVOG leaf hints · one value read from the payload once, equal to the five per-field lookups it replaces."""

from __future__ import annotations

import pytest
from discovery_ingest.harvest.pvog import LeafHints
from discovery_ingest.pvog.domain_mapping import PERSONAL_MATTER_DOMAIN_CLARITY, PERSONAL_MATTER_TO_DOMAIN
from discovery_ingest.pvog.situation_mapping import PERSONAL_MATTER_CLARITY, PERSONAL_MATTER_TO_SITUATION


def _expected(code: str | None) -> LeafHints:
    """The values the five functions returned before the refactor, spelled out from the tables."""
    if code is None:
        return LeafHints(None, None, None, None, None)
    return LeafHints(
        situation_codes=PERSONAL_MATTER_TO_SITUATION.get(code),
        situation_confidence=PERSONAL_MATTER_CLARITY.get(code),
        domain_codes=PERSONAL_MATTER_TO_DOMAIN.get(code),
        domain_confidence=PERSONAL_MATTER_DOMAIN_CLARITY.get(code),
        leaf_code=code,
    )


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
def test_leaf_hints_from_payload_matches_the_old_five_functions(code: str | None) -> None:
    """LeafHints · every field equals the table lookup the old per-field function returned."""
    payload: dict[str, object] = {"languageCode": "de"}
    if code is not None:
        payload["_personal_matter_code"] = code

    assert LeafHints.from_payload(payload) == _expected(code)


def test_leaf_hints_keeps_an_empty_code_as_the_leaf_code_without_any_mapping() -> None:
    """LeafHints · a stashed empty string is a code with no mapping, as the old functions treated it."""
    hints = LeafHints.from_payload({"_personal_matter_code": ""})

    assert hints.leaf_code == ""
    assert hints.situation_codes is None
    assert hints.domain_codes is None


def test_leaf_hints_ignores_a_non_string_code() -> None:
    """LeafHints · a stashed value that is not a string is no code at all."""
    assert LeafHints.from_payload({"_personal_matter_code": 1180100}) == LeafHints(None, None, None, None, None)
