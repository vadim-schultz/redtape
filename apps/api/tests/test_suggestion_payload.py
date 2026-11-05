from __future__ import annotations

from uuid import uuid4

import pytest
from app.schema.discovery.candidate_emit import PreviewedDocumentPayload
from app.schema.suggestion.create import SuggestionCreate
from app.schema.suggestion.payload import NewDocumentPayload
from pydantic import ValidationError


def _payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "title_i18n": {"en": "Registration certificate"},
        "official_url": "https://example.com/form",
    }
    base.update(overrides)
    return base


def test_accepts_a_minimal_valid_payload() -> None:
    payload = NewDocumentPayload.model_validate(_payload())
    assert payload.title_i18n == {"en": "Registration certificate"}
    assert payload.official_url == "https://example.com/form"


def test_accepts_a_new_document_payload_without_official_url() -> None:
    payload = NewDocumentPayload.model_validate({"title_i18n": {"de": "Personalausweis"}})
    assert payload.official_url is None


@pytest.mark.parametrize("url", ["", "   ", "example.com/form", "https://"])
def test_rejects_a_blank_or_malformed_official_url(url: str) -> None:
    with pytest.raises(ValidationError):
        NewDocumentPayload.model_validate(_payload(official_url=url))


def test_rejects_a_blank_title() -> None:
    with pytest.raises(ValidationError):
        NewDocumentPayload.model_validate(_payload(title_i18n={"en": "   "}))


def test_rejects_an_empty_title_map() -> None:
    with pytest.raises(ValidationError):
        NewDocumentPayload.model_validate(_payload(title_i18n={}))


def test_rejects_invalid_locale_codes() -> None:
    with pytest.raises(ValidationError):
        NewDocumentPayload.model_validate(_payload(title_i18n={"english": "Hello"}))


def test_rejects_control_characters_in_title() -> None:
    with pytest.raises(ValidationError):
        NewDocumentPayload.model_validate(_payload(title_i18n={"en": "Bad\x00value"}))


def test_trims_whitespace_from_title_values() -> None:
    payload = NewDocumentPayload.model_validate(_payload(title_i18n={"en": "  Hello  "}))
    assert payload.title_i18n["en"] == "Hello"


@pytest.mark.parametrize("url", ["ftp://example.com/form", "javascript:alert(1)"])
def test_rejects_a_non_http_url(url: str) -> None:
    with pytest.raises(ValidationError):
        NewDocumentPayload.model_validate(_payload(official_url=url))


def test_rejects_a_url_over_500_characters() -> None:
    host = "example.com"
    path_500 = "/" + "a" * (500 - len(f"https://{host}/"))
    url_500 = f"https://{host}{path_500}"
    assert len(url_500) == 500
    NewDocumentPayload.model_validate(_payload(official_url=url_500))

    url_501 = url_500 + "a"
    with pytest.raises(ValidationError):
        NewDocumentPayload.model_validate(_payload(official_url=url_501))


def test_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        NewDocumentPayload.model_validate(_payload(extra_field="nope"))


def test_rejects_duplicate_code_lists() -> None:
    with pytest.raises(ValidationError):
        NewDocumentPayload.model_validate(_payload(category_codes=["home-and-housing", "home-and-housing"]))


def test_rejects_oversized_code_lists() -> None:
    codes = [f"code{i}" for i in range(21)]
    with pytest.raises(ValidationError):
        NewDocumentPayload.model_validate(_payload(category_codes=codes))


def test_accepts_a_tag_confidence_key_present_in_either_code_list() -> None:
    payload = NewDocumentPayload.model_validate(
        _payload(
            category_codes=["home-and-housing", "moving-house"],
            tag_confidence={"home-and-housing": 0.85, "moving-house": 0.25},
        )
    )
    assert payload.tag_confidence == {"home-and-housing": 0.85, "moving-house": 0.25}


def test_rejects_a_tag_confidence_key_not_in_either_code_list() -> None:
    with pytest.raises(ValidationError):
        NewDocumentPayload.model_validate(_payload(category_codes=["home-and-housing"], tag_confidence={"other": 0.9}))


def test_accepts_a_pvog_leaf_codes_key_present_in_category_codes() -> None:
    payload = NewDocumentPayload.model_validate(
        _payload(category_codes=["moving-house"], pvog_leaf_codes={"moving-house": "1050200"})
    )
    assert payload.pvog_leaf_codes == {"moving-house": "1050200"}


def test_rejects_a_pvog_leaf_codes_key_not_in_category_codes() -> None:
    with pytest.raises(ValidationError):
        NewDocumentPayload.model_validate(
            _payload(category_codes=["moving-house"], pvog_leaf_codes={"other": "1050200"})
        )


def _create_request(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "kind": "new_document",
        "jurisdiction_id": str(uuid4()),
        "payload": _payload(),
    }
    base.update(overrides)
    return base


def test_suggestion_create_rejects_both_jurisdiction_id_and_municipality_code() -> None:
    with pytest.raises(ValidationError):
        SuggestionCreate.model_validate(_create_request(municipality_code="DE-BE"))


def test_suggestion_create_rejects_neither_jurisdiction_id_nor_municipality_code() -> None:
    with pytest.raises(ValidationError):
        SuggestionCreate.model_validate(_create_request(jurisdiction_id=None))


def test_the_emit_preview_payload_schema_advertises_no_legacy_axis_fields() -> None:
    advertised = set(PreviewedDocumentPayload.model_json_schema()["properties"])

    assert advertised.isdisjoint({"domain_codes", "situation_codes", "situation_leaf_codes"})
    assert "category_codes" in advertised
