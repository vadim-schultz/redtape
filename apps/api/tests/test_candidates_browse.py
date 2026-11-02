"""The public candidate list as a browsable document list: presence filters, several codes, confidence."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from app.features.candidates.list_query import codes_filter
from app.main import create_app
from litestar import Litestar
from litestar.testing import TestClient
from scripts.seed_taxonomy import seed_taxonomy
from sqlalchemy.orm import Session

from candidates_public_world import HOUSING, MOVING, Scene

URL = "/api/v1/candidates"
IDENTITY, VEHICLES = "identity-civil-status", "vehicles-mobility"
MARRIAGE = "marriage"


@pytest.fixture
def client(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient[Litestar]]:
    """A client on the test session with the taxonomy seeded; the routes under test are public."""
    seed_taxonomy(db_session, tags={})
    monkeypatch.setattr("app.main.provide_session", lambda: db_session)
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def scene(db_session: Session) -> Scene:
    return Scene(db_session)


def _keys(body: dict) -> list[str]:
    return [item["key"] for item in body["items"]]


def _get(client: TestClient[Litestar], **params: str) -> dict:
    response = client.get(URL, params=params)
    assert response.status_code == 200, response.text
    return response.json()


def _errors(client: TestClient[Litestar], **params: str) -> list[dict[str, str]]:
    response = client.get(URL, params=params)
    assert response.status_code == 422, response.text
    return response.json()["extra"]


def _below_the_old_floor(scene: Scene, key: str, code: str) -> None:
    """A candidate that carries ``code`` on one of 25 tagged procedures, so it scores 0.5 / 25 = 0.02 (< 0.05)."""
    owner = scene.candidate(key)
    scene.mention(owner, scene.procedure(), domains=[code])
    for _ in range(24):
        scene.mention(owner, scene.procedure(), domains=[VEHICLES])


# --- codes_filter -----------------------------------------------------------------------------------------------


def test_codes_filter_trims_and_deduplicates_into_a_normalised_csv() -> None:
    assert codes_filter(" housing , work,housing") == "housing,work"


@pytest.mark.parametrize(
    "raw",
    ["", "a,,b", "a,", ",a", " ", "x" * 65, ",".join(f"c{n}" for n in range(21))],
    ids=["empty", "empty-item", "trailing-comma", "leading-comma", "blank", "too-long", "too-many"],
)
def test_codes_filter_rejects_malformed_lists_with_a_client_message(raw: str) -> None:
    with pytest.raises(ValueError, match=r"\w"):
        codes_filter(raw)


def test_codes_filter_accepts_the_limits() -> None:
    assert codes_filter("x" * 64) == "x" * 64
    assert len(codes_filter(",".join(f"c{n}" for n in range(20))).split(",")) == 20


# --- presence filter --------------------------------------------------------------------------------------------


def test_a_chip_filter_matches_by_presence_whatever_the_score(client: TestClient[Litestar], scene: Scene) -> None:
    _below_the_old_floor(scene, "weak", HOUSING)
    scene.scored("strong", domains={HOUSING: 0.9})
    scene.scored("other", domains={VEHICLES: 0.9})

    body = _get(client, **{"filter[domain]": HOUSING})

    assert (set(_keys(body)), body["total"]) == ({"weak", "strong"}, 2)


def test_several_codes_of_one_axis_return_the_union(client: TestClient[Litestar], scene: Scene) -> None:
    scene.scored("housing-doc", domains={HOUSING: 0.5})
    scene.scored("identity-doc", domains={IDENTITY: 0.5})
    scene.scored("vehicle-doc", domains={VEHICLES: 0.5})
    scene.scored("both-doc", domains={HOUSING: 0.5, IDENTITY: 0.5})

    body = _get(client, **{"filter[domain]": f"{HOUSING},{IDENTITY}"})

    assert (set(_keys(body)), body["total"]) == ({"housing-doc", "identity-doc", "both-doc"}, 3)


def test_the_two_axes_return_the_intersection(client: TestClient[Litestar], scene: Scene) -> None:
    scene.scored("both", domains={HOUSING: 0.5}, situations={MOVING: 0.5})
    scene.scored("domain-only", domains={HOUSING: 0.5})
    scene.scored("situation-only", situations={MOVING: 0.5})
    scene.scored("wrong-situation", domains={HOUSING: 0.5}, situations={MARRIAGE: 0.5})

    body = _get(client, **{"filter[domain]": HOUSING, "filter[situation]": MOVING})

    assert (_keys(body), body["total"]) == (["both"], 1)


def test_a_candidate_with_the_code_on_the_other_axis_does_not_match(client: TestClient[Litestar], scene: Scene) -> None:
    scene.scored("situation-doc", situations={MOVING: 0.9})

    assert _get(client, **{"filter[domain]": HOUSING})["total"] == 0


def test_complete_still_narrows_a_chip_filter(client: TestClient[Litestar], scene: Scene) -> None:
    scene.complete_candidate("complete")
    scene.scored("scored-only", domains={HOUSING: 0.9})

    params = {"filter[domain]": HOUSING, "filter[complete]": "yes"}
    assert _keys(_get(client, **params)) == ["complete"]
    assert _keys(_get(client, **{**params, "filter[complete]": "no"})) == ["scored-only"]


def test_a_code_no_candidate_has_is_an_empty_page_not_an_error(client: TestClient[Litestar], scene: Scene) -> None:
    scene.scored("housing-doc", domains={HOUSING: 0.9})

    body = _get(client, **{"filter[domain]": VEHICLES})

    assert (body["items"], body["total"]) == ([], 0)


def test_repeating_a_code_matches_each_candidate_once(client: TestClient[Litestar], scene: Scene) -> None:
    scene.scored("doc", domains={HOUSING: 0.9})

    body = _get(client, **{"filter[domain]": f"{HOUSING},{HOUSING}"})

    assert (_keys(body), body["total"]) == (["doc"], 1)


# --- rejected input ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("axis", ["domain", "situation"])
@pytest.mark.parametrize(
    "raw",
    [",".join(f"c{n}" for n in range(21)), "a,,b", "x" * 65],
    ids=["21-codes", "empty-item", "65-characters"],
)
def test_a_malformed_code_list_is_a_422_naming_the_parameter(client: TestClient[Litestar], axis: str, raw: str) -> None:
    errors = _errors(client, **{f"filter[{axis}]": raw})

    assert [error["key"] for error in errors] == [f"filter[{axis}]"]


def test_an_unknown_code_is_a_422_naming_that_code(client: TestClient[Litestar], scene: Scene) -> None:
    errors = _errors(client, **{"filter[domain]": f"{HOUSING},nope"})

    assert [(error["key"], error["message"]) for error in errors] == [("filter[domain]", "Unknown code: nope")]


def test_two_unknown_codes_are_two_errors(client: TestClient[Litestar], scene: Scene) -> None:
    errors = _errors(client, **{"filter[domain]": "nope,nada", "filter[situation]": f"{MOVING},never"})

    assert [(error["key"], error["message"]) for error in errors] == [
        ("filter[domain]", "Unknown code: nope"),
        ("filter[domain]", "Unknown code: nada"),
        ("filter[situation]", "Unknown code: never"),
    ]


def test_sort_order_without_sort_by_is_still_a_422(client: TestClient[Litestar]) -> None:
    assert [error["key"] for error in _errors(client, sort_order="desc")] == ["sort_order"]
