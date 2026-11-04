"""C4 contract tests for canonical category evidence."""

from __future__ import annotations

from uuid import UUID

import pytest
from discovery_ingest.curation import CurationFile
from discovery_ingest.curation_check import code_problems
from discovery_ingest.extract.clean import CleanPage
from discovery_ingest.extract.llm.ground import ground
from discovery_ingest.extract.llm.schema import PageExtraction, build_json_schema
from discovery_ingest.extract.llm.taxonomy import Taxonomy, TaxonomyTerm
from discovery_ingest.harvest.pvog import harvest_pvog_payload
from discovery_ingest.mentions import MentionItem
from discovery_ingest.pvog.models import PvogSourcePath
from pydantic import ValidationError

SERVICE_ID = UUID("00000000-0000-0000-0000-000000000001")
ARTIFACT_ID = UUID("00000000-0000-0000-0000-000000000002")


def _taxonomy() -> Taxonomy:
    return Taxonomy(
        categories=(
            TaxonomyTerm(
                code="moving-house",
                name_i18n={"de": "Umzug"},
                description_i18n={"de": "Wohnsitz wechseln"},
                parent_code="home-and-housing",
            ),
            TaxonomyTerm(
                code="retirement",
                name_i18n={"de": "Renteneintritt"},
                description_i18n={"de": "Rente beantragen"},
                parent_code="retirement-and-old-age",
            ),
        ),
        digest="category-digest",
        source_version="category-contract-v1",
    )


def _document() -> dict[str, str]:
    return {
        "name": "Meldebescheinigung",
        "role": "required",
        "quote": "Bitte bringen Sie die Meldebescheinigung mit.",
    }


def _extraction(**changes: object) -> dict[str, object]:
    return {
        "page_kind": "service",
        "category_codes": ["moving-house"],
        "documents": [_document()],
        "dependencies": [],
        **changes,
    }


def test_mention_accepts_canonical_category_codes_and_preserves_pvog_source_facts() -> None:
    mention = MentionItem(
        catalogue_service_id=SERVICE_ID,
        artifact_id=ARTIFACT_ID,
        title_i18n={"de": "Meldebescheinigung"},
        role="required",
        excerpt="Bitte bringen Sie die Meldebescheinigung mit.",
        source_field="details[code=08]",
        extractor="pvog-payload",
        extractor_version="2",
        category_codes=["moving-house"],
        direct_category_confidence=0.95,
        pvog_leaf_code="1050200",
        pvog_source_path=PvogSourcePath(
            root_code="1",
            root_label="Lebenslagen für Bürgerinnen und Bürger",
            parent_code="105",
            parent_label="Bauen und Wohnen",
            leaf_code="1050200",
            leaf_label="Wohnen und Umzug",
            source_version="v7",
        ),
        pvog_mapping_version="category-contract-v1",
    )

    assert mention.category_codes == ["moving-house"]
    assert mention.pvog_leaf_code == "1050200"
    assert mention.pvog_source_path.parent_label == "Bauen und Wohnen"
    assert mention.pvog_source_path.source_version == "v7"
    assert mention.pvog_mapping_version == "category-contract-v1"


def test_pvog_harvest_maps_a_known_parent_leaf_through_the_frozen_crosswalk() -> None:
    drafts = harvest_pvog_payload(
        {
            "details": [
                {
                    "code": "08",
                    "filled": True,
                    "text": "<ul><li>Meldebescheinigung</li></ul>",
                    "links": [],
                }
            ],
            "_pvog_source_path": {
                "root_code": "1",
                "root_label": "Lebenslagen für Bürgerinnen und Bürger",
                "parent_code": "105",
                "parent_label": "Bauen und Wohnen",
                "leaf_code": "1050200",
                "leaf_label": "Wohnen und Umzug",
                "source_version": "v7",
            },
        }
    )

    assert drafts[0].category_codes == ["moving-house", "renting-home"]
    assert drafts[0].direct_category_confidence == 0.65
    assert drafts[0].pvog_leaf_code == "1050200"
    assert drafts[0].pvog_source_path is not None
    assert drafts[0].pvog_source_path.root_label == "Lebenslagen für Bürgerinnen und Bürger"
    assert drafts[0].pvog_mapping_version == "category-contract-v1"


def test_pvog_missing_path_retains_leaf_provenance_but_emits_no_invented_category() -> None:
    drafts = harvest_pvog_payload(
        {
            "details": [
                {
                    "code": "08",
                    "filled": True,
                    "text": "<ul><li>Meldebescheinigung</li></ul>",
                    "links": [],
                }
            ],
            "_personal_matter_code": "1050200",
        }
    )

    assert drafts[0].pvog_leaf_code == "1050200"
    assert drafts[0].category_codes is None
    assert drafts[0].direct_category_confidence is None
    assert drafts[0].pvog_source_path is None


def test_llm_schema_offers_only_active_category_codes() -> None:
    schema = build_json_schema(_taxonomy())

    assert schema["properties"]["category_codes"]["items"]["enum"] == ["moving-house", "retirement"]
    assert schema["properties"]["category_codes"]["maxItems"] == 5
    assert "domain_codes" not in schema["properties"]
    assert "situation_codes" not in schema["properties"]


def test_llm_schema_rejects_legacy_domain_and_situation_output() -> None:
    with pytest.raises(ValidationError, match="legacy"):
        PageExtraction.model_validate(
            {
                "page_kind": "service",
                "domain_codes": ["housing"],
                "situation_codes": ["moving-house"],
                "documents": [_document()],
                "dependencies": [],
            }
        )


def test_llm_schema_rejects_an_unknown_category_code() -> None:
    extraction = PageExtraction.model_validate(_extraction(category_codes=["not-in-vocabulary"]))

    grounded = ground(
        extraction,
        CleanPage(
            text="Bitte bringen Sie die Meldebescheinigung mit.",
            links=frozenset(),
            language="de",
            title=None,
            truncated=False,
            version="test",
        ),
        _taxonomy(),
    )

    assert grounded.category_codes == ()
    assert grounded.diagnostics.unknown_codes == 1


def test_manual_curation_reports_a_category_from_another_taxonomy_version() -> None:
    curation = CurationFile.model_validate(
        {
            "version": 1,
            "curator": "test",
            "candidates": [
                {
                    "candidate_id": str(SERVICE_ID),
                    "catalogue_service_id": str(ARTIFACT_ID),
                    "title_de": "Meldebescheinigung",
                    "category_codes": ["stale-code"],
                    "tag_note": "stale fixture",
                }
            ],
        }
    )

    assert code_problems(curation, _taxonomy()) == ["'Meldebescheinigung' category_codes: unknown code 'stale-code'"]
