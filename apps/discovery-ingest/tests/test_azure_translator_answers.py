"""Azure answers · every answer is matched by position; a short, misaligned or malformed answer is unusable and stores nothing."""

from __future__ import annotations

import httpx
import pytest
from discovery_ingest.translation.errors import UnusableOutputError

from azure_transport import engine, faithful_answer
from translation_fakes import batch, unit

TWO_UNITS = batch(unit("a", "Antrag", "Gebühr"), unit("b", "Wohngeld"), target="ro")


def _answering(body: object) -> httpx.Response:
    return httpx.Response(200, json=body, headers={"X-metered-usage": "1"})


def test_an_answer_with_fewer_translations_than_inputs_raises_unusable_output_and_stores_nothing() -> None:
    """Azure · an answer with fewer translations than inputs raises UnusableOutputError and stores nothing."""

    def handler(request: httpx.Request) -> httpx.Response:
        return faithful_answer(request, drop=1)

    with pytest.raises(UnusableOutputError, match="3 translations"):
        engine(handler).translate(TWO_UNITS)


@pytest.mark.parametrize(
    "body",
    [
        [{"translations": [{"text": "x", "to": "tr"}]}] * 3,
        [{"translations": [{"text": "x", "to": "ro"}]}, {"translations": []}, {"translations": [{"text": "y"}]}],
        [{"translations": [{"text": "x", "to": "ro"}]}, {"translations": [{"text": 5, "to": "ro"}]}, {"oops": 1}],
        {"error": {"code": 500000, "message": "no list"}},
    ],
    ids=["another-target", "empty-translations", "off-schema-item", "not-a-list"],
)
def test_an_answer_for_another_target_or_of_another_shape_is_unusable(body: object) -> None:
    """Azure · an answer that names another target, has no translation, or is not a list of answers is unusable."""
    adapter = engine(lambda _request: _answering(body))

    with pytest.raises(UnusableOutputError):
        adapter.translate(batch(unit("a", "Antrag"), unit("b", "Wohngeld"), unit("c", "Pflege"), target="ro"))


def test_an_answer_that_is_not_json_is_unusable() -> None:
    """Azure · a 200 answer whose body is not JSON is unusable output, not a transient error."""

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"<html>gateway</html>", headers={"X-metered-usage": "1"})

    with pytest.raises(UnusableOutputError):
        engine(handler).translate(TWO_UNITS)


def test_answers_are_matched_by_position_and_a_missing_field_stays_blank() -> None:
    """Azure · the answers fill the title and description of each unit by position; a blank field is left blank."""

    def handler(request: httpx.Request) -> httpx.Response:
        return faithful_answer(request)

    outcome = engine(handler).translate(TWO_UNITS)

    assert [(result.title, result.description) for result in outcome.results] == [
        ("[en] Antrag", "[en] Gebühr"),
        ("[en] Wohngeld", ""),
    ]
