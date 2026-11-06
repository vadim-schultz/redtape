"""PERSONAL_MATTER_TO_SITUATION table shape (chapter 3, T4 widened sign-off) and its mapping-clarity
weights (situation-tag-hierarchy chapter 3)."""

from __future__ import annotations

from discovery_ingest.mentions import MAX_SITUATION_CODES
from discovery_ingest.pvog.models import PvogSourcePath
from discovery_ingest.pvog.situation_mapping import (
    PERSONAL_MATTER_CLARITY,
    PERSONAL_MATTER_TO_SITUATION,
)

from crosswalk_fakes import CROSSWALK

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


def test_clarity_table_has_exactly_the_same_keys_as_the_situation_table() -> None:
    """Clarity · PERSONAL_MATTER_CLARITY never drifts from PERSONAL_MATTER_TO_SITUATION's key set."""
    assert set(PERSONAL_MATTER_CLARITY) == set(PERSONAL_MATTER_TO_SITUATION)


def test_clarity_table_values_are_one_of_the_two_reviewed_weights() -> None:
    """Clarity · every weight is 0.95 (clean) or 0.65 (ambiguous), per lr3-personal-matters-mapping.md."""
    assert set(PERSONAL_MATTER_CLARITY.values()) == {0.95, 0.65}


def test_clarity_table_marks_18_clean_leaves_and_14_ambiguous_leaves() -> None:
    """Clarity · the 18/14 clean/ambiguous split matches T4's tally exactly."""
    clean = [code for code, weight in PERSONAL_MATTER_CLARITY.items() if weight == 0.95]
    ambiguous = [code for code, weight in PERSONAL_MATTER_CLARITY.items() if weight == 0.65]
    assert len(clean) == 18
    assert len(ambiguous) == 14


def test_clarity_table_cites_the_sign_off_verdict_for_known_clean_and_ambiguous_leaves() -> None:
    """Clarity · spot-check a few leaves against lr3-personal-matters-mapping.md's verdict column."""
    assert PERSONAL_MATTER_CLARITY["1010100"] == 0.95  # clean: Vor der Geburt
    assert PERSONAL_MATTER_CLARITY["1030300"] == 0.95  # clean: Studium
    assert PERSONAL_MATTER_CLARITY["1180100"] == 0.95  # clean: Altersvorsorge
    assert PERSONAL_MATTER_CLARITY["1040300"] == 0.65  # ambiguous: Jobsuche und Arbeitslosigkeit
    assert PERSONAL_MATTER_CLARITY["1050200"] == 0.65  # ambiguous: Wohnen und Umzug
    assert PERSONAL_MATTER_CLARITY["1140100"] == 0.65  # ambiguous: Existenzsicherung


def test_category_mapping_preserves_source_leaf_and_maps_to_product_categories() -> None:
    """Category mapping · a known complete PVOG path emits canonical evidence."""
    path = PvogSourcePath(
        root_code="1",
        root_label="Lebenslagen für Bürgerinnen und Bürger",
        parent_code="118",
        parent_label="Altersvorsorge und Ruhestand",
        leaf_code="1180100",
        leaf_label="Altersvorsorge",
        source_version="v7",
    )

    evidence = CROSSWALK.evidence_for_path(path)

    assert evidence is not None
    assert evidence.category_codes == ("retirement",)
    assert evidence.leaf_code == "1180100"
    assert evidence.source_path == path
    assert evidence.confidence == CROSSWALK.leaves["1180100"].confidence
    assert CROSSWALK.leaves["1180100"].category_codes == ("retirement",)
    assert "1180100" not in evidence.category_codes


def _path_under_own_parent(leaf_code: str) -> PvogSourcePath:
    """Return a complete PVOG path whose parent is the leaf's own parent (the first three digits)."""
    return PvogSourcePath(
        root_code="1",
        root_label="Lebenslagen für Bürgerinnen und Bürger",
        parent_code=leaf_code[:3],
        parent_label="Parent",
        leaf_code=leaf_code,
        leaf_label="Leaf",
        source_version="v7",
    )


# Leaves whose own PVOG parent is not a source parent of their frozen target category, so harvest emits no evidence.
# 1040100 (Weiterbildung) sits under parent 104 but targets education-and-training, whose source parent is 103.
# 1060700 (Erbschaftsteuer and Schenkungsteuer) sits under parent 106 but targets death-and-estate, whose source
# parent is 119. The category inventory is frozen (D-R5), and the user kept both targets on 2026-11-06.
HARVEST_EVIDENCE_EXEMPT = frozenset({"1040100", "1060700"})


def test_harvest_emits_mapped_evidence_with_a_reason_for_every_pvog_leaf() -> None:
    """Happy path (D-R9): each PVOG leaf emits mapped harvest evidence with a reason, except the named exemptions."""
    emitted = {
        leaf_code: CROSSWALK.evidence_for_path(_path_under_own_parent(leaf_code)) for leaf_code in CROSSWALK.leaves
    }

    assert {leaf for leaf, evidence in emitted.items() if evidence is None} == HARVEST_EVIDENCE_EXEMPT
    for leaf_code, evidence in emitted.items():
        if leaf_code in HARVEST_EVIDENCE_EXEMPT:
            continue
        assert evidence is not None, leaf_code
        assert evidence.state == "mapped", leaf_code
        assert evidence.reason.strip(), leaf_code


def test_category_mapping_does_not_invent_category_for_an_unmapped_leaf() -> None:
    """Category mapping · a source-only leaf has no canonical category evidence."""
    path = PvogSourcePath(
        root_code="1",
        root_label="Lebenslagen für Bürgerinnen und Bürger",
        parent_code="117",
        parent_label="Umwelt und Klima",
        leaf_code="1170100",
        leaf_label="Klima, Natur und Arten",
        source_version="v7",
    )

    assert CROSSWALK.evidence_for_path(path) is None
