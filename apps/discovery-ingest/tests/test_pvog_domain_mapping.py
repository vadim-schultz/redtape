"""PERSONAL_MATTER_TO_DOMAIN table shape (situation-tag-hierarchy chapter 3, P3 resolved)."""

from __future__ import annotations

from discovery_ingest.mentions import MAX_DOMAIN_CODES
from discovery_ingest.pvog.domain_mapping import PERSONAL_MATTER_DOMAIN_CLARITY, PERSONAL_MATTER_TO_DOMAIN
from discovery_ingest.pvog.situation_mapping import PERSONAL_MATTER_TO_SITUATION

DOMAIN_CODES = {
    "identity-civil-status",
    "housing",
    "vehicles-mobility",
    "work-employment",
    "family-children",
    "education",
    "health-insurance",
    "taxes-finance",
    "residence-migration",
    "retirement-old-age",
    "self-employment-business",
    "social-benefits",
    "law-justice",
}


def test_table_has_14_entries() -> None:
    """Table · recovers a domain hint for 14 of the 24 unmapped citizen leaves."""
    assert len(PERSONAL_MATTER_TO_DOMAIN) == 14


def test_every_key_is_a_pvog_leaf_code_string() -> None:
    """Table · every key is a non-empty string PVOG leaf code."""
    for key in PERSONAL_MATTER_TO_DOMAIN:
        assert isinstance(key, str)
        assert key.strip()


def test_every_value_is_a_non_empty_list_of_known_domain_codes_within_max_length() -> None:
    """Table · every value is a non-empty list drawn from the 13 existing domains, length <= MAX_DOMAIN_CODES."""
    for codes in PERSONAL_MATTER_TO_DOMAIN.values():
        assert isinstance(codes, list)
        assert 1 <= len(codes) <= MAX_DOMAIN_CODES
        assert set(codes) <= DOMAIN_CODES


def test_covers_exactly_the_six_domains_the_design_names() -> None:
    """Table · recovers taxes-finance, identity-civil-status, law-justice, social-benefits, education,
    family-children — no other domain gets a PVOG leaf hint."""
    covered = {code for codes in PERSONAL_MATTER_TO_DOMAIN.values() for code in codes}
    assert covered == {
        "taxes-finance",
        "identity-civil-status",
        "law-justice",
        "social-benefits",
        "education",
        "family-children",
    }


def test_leaf_groupings_match_the_design_table() -> None:
    """Table · spot-check each domain's leaf group against the chapter design's table."""
    by_domain: dict[str, list[str]] = {}
    for code, domains in PERSONAL_MATTER_TO_DOMAIN.items():
        [domain] = domains
        by_domain.setdefault(domain, []).append(code)

    assert sorted(by_domain["taxes-finance"]) == ["1060100", "1060200", "1060300", "1060800"]
    assert sorted(by_domain["identity-civil-status"]) == ["1070100", "1070200"]
    assert sorted(by_domain["law-justice"]) == ["1150100", "1150200", "1150300", "1150400"]
    assert sorted(by_domain["social-benefits"]) == ["1160100", "1160200"]
    assert by_domain["education"] == ["1040100"]
    assert by_domain["family-children"] == ["1020200"]


def test_clarity_table_has_exactly_the_same_keys_flat_at_point_eight() -> None:
    """Clarity · all 14 leaves get a flat 0.8 — lower than the situation axis's reviewed 0.95, reflecting
    that this table is a first pass (P3)."""
    assert set(PERSONAL_MATTER_DOMAIN_CLARITY) == set(PERSONAL_MATTER_TO_DOMAIN)
    assert set(PERSONAL_MATTER_DOMAIN_CLARITY.values()) == {0.8}


def test_the_14_domain_hint_leaves_come_from_the_24_unmapped_citizen_leaves_not_the_32_mapped_ones() -> None:
    """Table · the two mappings are allowed to overlap by design, but today's 14 domain-hint leaves are
    drawn from the unmapped pool, so none of them coincides with PERSONAL_MATTER_TO_SITUATION's 32 keys —
    confirming neither table silently drops a leaf the other expects."""
    assert set(PERSONAL_MATTER_TO_DOMAIN).isdisjoint(PERSONAL_MATTER_TO_SITUATION)
