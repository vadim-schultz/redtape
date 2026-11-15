"""Azure chunking and usage · requests stay within 500 inputs and 40,000 characters, answers keep input order, and the bill is the header."""

from __future__ import annotations

import json

import httpx
import pytest
from discovery_ingest.translation.errors import PermanentError, RateLimited
from discovery_ingest.translation.units import Usage

from azure_transport import Handler, engine, failure, faithful_answer, inputs_in
from translation_fakes import batch, unit


def _recording(seen: list[httpx.Request], metered: float | None = None) -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return faithful_answer(request, metered=metered)

    return handler


def test_600_inputs_split_into_two_requests_of_at_most_500_inputs_and_answers_in_input_order() -> None:
    """Azure · 600 inputs split into two requests of at most 500 inputs and 40,000 characters, answers in input order."""
    seen: list[httpx.Request] = []
    units = [unit(f"u{number:03d}", f"Antrag {number}") for number in range(600)]

    outcome = engine(_recording(seen)).translate(batch(*units))

    assert [len(inputs_in(request)) for request in seen] == [500, 100]
    assert [result.key for result in outcome.results] == [source.key for source in units]
    assert [result.title for result in outcome.results] == [f"[en] Antrag {number}" for number in range(600)]


def test_a_request_never_exceeds_28000_characters_and_the_split_keeps_order() -> None:
    """Azure · three texts of 15,000 characters go as three requests, each within the 28,000 a minute the window admits."""
    seen: list[httpx.Request] = []
    units = [unit(key, "x" * 15_000) for key in ("a", "b", "c")]

    outcome = engine(_recording(seen)).translate(batch(*units))

    sizes = [sum(len(str(item["text"])) for item in inputs_in(request)) for request in seen]
    assert len(seen) == 3 and all(size <= 28_000 for size in sizes)
    assert [result.key for result in outcome.results] == ["a", "b", "c"]


def _lead(request: httpx.Request) -> str:
    """The first character of the first text of a request: the number of the unit it carries."""
    return str(inputs_in(request)[0]["text"])[0]


def test_a_retry_of_chunk_three_does_not_re_bill_chunks_one_and_two() -> None:
    """Azure · a page whose third request is throttled keeps chunks one and two; the retry sends only chunk three again."""
    sent: dict[str, int] = {}
    throttled = [True]

    def handler(request: httpx.Request) -> httpx.Response:
        lead = _lead(request)
        sent[lead] = sent.get(lead, 0) + 1
        if lead == "3" and throttled[0]:
            return failure(429, "429000", "slow")
        return faithful_answer(request)

    adapter = engine(handler)
    page = batch(*(unit(key, key + "x" * 19_999) for key in ("1", "2", "3")))
    with pytest.raises(RateLimited):
        adapter.translate(page)
    throttled[0] = False

    outcome = adapter.translate(page)

    assert sent == {"1": 1, "2": 1, "3": 4}
    assert outcome.usage.amount == 60_000
    assert [result.key for result in outcome.results] == ["1", "2", "3"]


def test_a_text_over_the_request_limit_is_refused_before_anything_is_sent() -> None:
    """Azure · a single text over 40,000 characters is a permanent error and no request leaves the adapter."""
    seen: list[httpx.Request] = []

    with pytest.raises(PermanentError, match="longer than one request"):
        engine(_recording(seen)).translate(batch(unit("a", "x" * 40_001)))

    assert seen == []


def test_usage_is_the_sum_of_x_metered_usage_over_the_chunks_not_the_estimate() -> None:
    """Azure · usage is the sum of X-metered-usage over chunks, not the estimate."""
    seen: list[httpx.Request] = []
    units = [unit(f"u{number:03d}", f"Antrag {number}") for number in range(600)]
    adapter = engine(_recording(seen, metered=7.0))

    outcome = adapter.translate(batch(*units))

    assert len(seen) == 2
    assert outcome.usage == Usage("characters", 14.0)
    assert adapter.estimate(batch(*units)).amount != outcome.usage.amount


def test_the_estimate_counts_the_source_characters_of_every_input_sent() -> None:
    """Azure · the estimate is the source characters of the title and description inputs; a blank description adds nothing."""
    estimate = engine(_recording([])).estimate(batch(unit("a", "Antrag", "Gebühr"), unit("b", "Wohngeld", "")))

    assert estimate == Usage("characters", float(len("Antrag") + len("Gebühr") + len("Wohngeld")))


def test_a_blank_description_is_not_sent_and_comes_back_blank() -> None:
    """Azure · an empty description is skipped: one input for the unit, and the unit's description stays empty."""
    seen: list[httpx.Request] = []

    outcome = engine(_recording(seen)).translate(batch(unit("a", "Antrag", "")))

    assert [item["text"] for item in inputs_in(seen[0])] == ["Antrag"]
    assert json.loads(seen[0].content)["inputs"][0]["textType"] == "plain"
    assert outcome.results[0].description == ""
