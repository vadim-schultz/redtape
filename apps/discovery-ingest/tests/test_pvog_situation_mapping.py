"""PVOG leaf evidence through the served crosswalk (chapter C7 removed the legacy situation table)."""

from __future__ import annotations

from discovery_ingest.pvog.models import PvogSourcePath

from crosswalk_fakes import CROSSWALK


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
