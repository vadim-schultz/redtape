"""Azure request · one target per call, the key and region headers, no key in the body, and the locale map."""

from __future__ import annotations

import json

import httpx
import pytest
from discovery_ingest.translation.locale_codes import DEFAULT_TARGET_LOCALES, provider_code
from discovery_ingest.translation.units import TranslationOutcome

from azure_transport import API_VERSION, ENDPOINT, KEY, REGION, Handler, engine, faithful_answer
from translation_fakes import batch, unit


def _capture() -> tuple[list[httpx.Request], Handler]:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return faithful_answer(request)

    return seen, handler


def test_request_carries_one_target_the_key_and_region_headers_and_no_key_in_the_body() -> None:
    """Azure · request carries one target, the key and region headers, and no key in the body."""
    seen, handler = _capture()

    engine(handler).translate(batch(unit("a", "Antrag", "Gebühr"), target="tr"))

    (request,) = seen
    body = json.loads(request.content)
    assert request.headers["Ocp-Apim-Subscription-Key"] == KEY
    assert request.headers["Ocp-Apim-Subscription-Region"] == REGION
    assert request.headers["X-ClientTraceId"]
    assert KEY.encode() not in request.content
    assert {"language": "tr"} in [target for item in body["inputs"] for target in item["targets"]]
    assert all(len(item["targets"]) == 1 for item in body["inputs"])


def test_each_input_is_german_plain_text_with_its_text_and_one_target() -> None:
    """Azure · every input names the German source, textType plain and exactly one target; title and description are separate inputs."""
    seen, handler = _capture()

    engine(handler).translate(batch(unit("a", "Antrag", "Gebühr"), target="ro"))

    (request,) = seen
    assert json.loads(request.content)["inputs"] == [
        {"text": "Antrag", "language": "de", "textType": "plain", "targets": [{"language": "ro"}]},
        {"text": "Gebühr", "language": "de", "textType": "plain", "targets": [{"language": "ro"}]},
    ]


def test_the_request_is_posted_to_translate_with_the_pinned_api_version() -> None:
    """Azure · the request goes to {endpoint}/translate?api-version=2026-06-06 as a POST."""
    seen, handler = _capture()

    engine(handler).translate(batch(unit("a", "Antrag"), target="en"))

    (request,) = seen
    assert request.method == "POST"
    assert str(request.url) == f"{ENDPOINT}/translate?api-version={API_VERSION}"


def test_the_locale_map_covers_en_tr_ru_uk_pl_ro_and_maps_each_to_itself() -> None:
    """Azure · locale map covers en tr ru uk pl ro and maps each to itself."""
    assert DEFAULT_TARGET_LOCALES == ("en", "tr", "ru", "uk", "pl", "ro")
    for code in DEFAULT_TARGET_LOCALES:
        assert provider_code("azure-translator", code) == code


def test_the_adapter_answers_one_result_per_unit_in_order_with_the_target_text() -> None:
    """Azure · a faithful answer maps back to the units by position, with the title and description of each."""
    _, handler = _capture()

    outcome = engine(handler).translate(batch(unit("a", "Antrag", "Gebühr"), unit("b", "Wohngeld"), target="pl"))

    assert isinstance(outcome, TranslationOutcome)
    assert [(result.key, result.title, result.description) for result in outcome.results] == [
        ("a", "[en] Antrag", "[en] Gebühr"),
        ("b", "[en] Wohngeld", ""),
    ]
    assert outcome.model is None


@pytest.mark.parametrize("header", [None, "not-a-number"])
def test_a_missing_or_unreadable_usage_header_bills_the_source_characters(header: str | None) -> None:
    """Azure · without a usable X-metered-usage header the billed amount is the characters sent, never zero."""

    def handler(request: httpx.Request) -> httpx.Response:
        response = faithful_answer(request)
        if header is None:
            del response.headers["X-metered-usage"]
        else:
            response.headers["X-metered-usage"] = header
        return response

    outcome = engine(handler).translate(batch(unit("a", "Antrag", "Gebühr")))

    assert outcome.usage.amount == float(len("Antrag") + len("Gebühr"))
