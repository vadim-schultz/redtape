"""C4 API contract tests for canonical category evidence."""

from __future__ import annotations

from unittest.mock import Mock
from uuid import UUID

import pytest
from app.features.discovery.candidate_codes import CodeVocabulary
from app.features.taxonomy.service import TaxonomyService
from app.schema.discovery.candidates import CandidateMentionItem
from app.schema.suggestion.payload import NewDocumentPayload
from pydantic import ValidationError


def _mention(**changes: object) -> dict[str, object]:
    return {
        "catalogue_service_id": "00000000-0000-0000-0000-000000000001",
        "title_i18n": {"de": "Meldebescheinigung"},
        "role": "required",
        "excerpt": "Bitte bringen Sie die Meldebescheinigung mit.",
        "source_field": "details[code=08]",
        "extractor": "pvog-payload",
        "extractor_version": "2",
        **changes,
    }


def test_canonical_mention_accepts_category_codes_and_pvog_provenance() -> None:
    mention = CandidateMentionItem.model_validate(
        _mention(
            category_codes=["moving-house"],
            direct_category_confidence=0.95,
            pvog_leaf_code="1050200",
            pvog_source_path={
                "root_code": "1",
                "root_label": "Lebenslagen für Bürgerinnen und Bürger",
                "parent_code": "105",
                "parent_label": "Bauen und Wohnen",
                "leaf_code": "1050200",
                "leaf_label": "Wohnen und Umzug",
                "source_version": "v7",
            },
            pvog_mapping_version="category-contract-v1",
        )
    )

    assert mention.category_codes == ["moving-house"]
    assert mention.pvog_source_path.parent_code == "105"
    assert mention.pvog_source_path.source_version == "v7"


def test_unknown_category_codes_are_reported_without_dropping_known_categories() -> None:
    item = CandidateMentionItem.model_validate(_mention(category_codes=["moving-house", "stale-code"]))
    taxonomy = Mock(spec=TaxonomyService)
    taxonomy.known_category_codes.return_value = {"moving-house"}

    vocabulary = CodeVocabulary.for_items([item], taxonomy)
    filtered = vocabulary.filter(item)

    assert filtered.category_codes == ["moving-house"]
    assert filtered.dropped == 1


def test_new_document_payload_translates_legacy_axis_fields_once() -> None:
    payload = NewDocumentPayload.model_validate(
        {
            "title_i18n": {"de": "Meldebescheinigung"},
            "domain_codes": ["housing"],
            "situation_codes": ["moving-house"],
        }
    )

    assert payload.category_codes == ["home-and-housing", "moving-house"]


def test_new_document_payload_rejects_stale_category_codes() -> None:
    with pytest.raises(ValidationError):
        NewDocumentPayload.model_validate(
            {
                "title_i18n": {"de": "Meldebescheinigung"},
                "category_codes": ["stale-code"],
            }
        )


def test_category_code_items_use_a_bounded_type() -> None:
    item = CandidateMentionItem.model_validate(_mention(category_codes=["moving-house"]))

    assert isinstance(item.catalogue_service_id, UUID)
