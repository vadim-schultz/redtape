"""PERSONAL_MATTER_TO_SITUATION table shape (chapter 3, T4 widened sign-off)."""

from __future__ import annotations

from discovery_ingest.mentions import MAX_SITUATION_CODES
from discovery_ingest.pvog.situation_mapping import PERSONAL_MATTER_TO_SITUATION

SITUATION_CODES = {
    "moving-house",
    "birth-of-child",
    "marriage",
    "separation-divorce",
    "death-of-relative",
    "job-loss",
    "new-job",
    "going-self-employed",
    "studying",
    "starting-school",
    "renting-home",
    "buying-property",
    "buying-vehicle",
    "getting-licence",
    "immigration",
    "naturalisation",
    "illness-care",
    "retirement",
}


def test_table_has_32_entries_per_t4_widened_sign_off() -> None:
    """Table · 18 clean + 14 ambiguous leaves, per T4."""
    assert len(PERSONAL_MATTER_TO_SITUATION) == 32


def test_every_key_is_a_pvog_leaf_code_string() -> None:
    """Table · every key is a non-empty string PVOG leaf code."""
    for key in PERSONAL_MATTER_TO_SITUATION:
        assert isinstance(key, str)
        assert key.strip()


def test_every_value_is_a_non_empty_list_of_valid_situation_codes_within_max_length() -> None:
    """Table · every value is a non-empty list drawn from the 18 situation codes, length <= MAX_SITUATION_CODES."""
    for codes in PERSONAL_MATTER_TO_SITUATION.values():
        assert isinstance(codes, list)
        assert 1 <= len(codes) <= MAX_SITUATION_CODES
        assert set(codes) <= SITUATION_CODES


def test_covers_17_of_18_situation_codes_going_self_employed_stays_unmapped() -> None:
    """Table · widened mapping reaches 17 of 18 codes; going-self-employed has no citizen leaf."""
    covered = {code for codes in PERSONAL_MATTER_TO_SITUATION.values() for code in codes}

    assert covered == SITUATION_CODES - {"going-self-employed"}


def test_bundled_leaves_emit_every_plausible_code() -> None:
    """Table · a bundled/ambiguous leaf emits all plausible codes, not just one."""
    assert PERSONAL_MATTER_TO_SITUATION["1040300"] == ["job-loss", "new-job"]
    assert PERSONAL_MATTER_TO_SITUATION["1050200"] == ["moving-house", "renting-home"]
