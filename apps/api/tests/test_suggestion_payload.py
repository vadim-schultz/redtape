from __future__ import annotations

from uuid import uuid4

import pytest
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
        NewDocumentPayload.model_validate(_payload(domain_codes=["housing", "housing"]))


def test_rejects_oversized_code_lists() -> None:
    codes = [f"code{i}" for i in range(21)]
    with pytest.raises(ValidationError):
        NewDocumentPayload.model_validate(_payload(domain_codes=codes))


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
