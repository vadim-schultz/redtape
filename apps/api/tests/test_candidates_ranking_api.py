"""``GET /api/v1/candidates`` ordered by the combined relevance and confidence score."""

from __future__ import annotations

import pytest
from app.config import settings
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy.orm import Session

from candidates_public_world import HOUSING, Scene
from query_embedder_support import FakeQueryEmbedder
from search_api_fixtures import URL, indexed_scored, keys, serve_with, vector_for
from search_query_world import indexed

QUERY = {"q": "kindergeld"}


def _pool(session: Session, scene: Scene) -> None:
    """Three vector-only matches: ``best-match`` is the closest, ``supported`` the best evidenced."""
    indexed_scored(session, scene, "best-match", "Irgendetwas Alpha", {HOUSING: 0.1}, similarity=0.9)
    indexed_scored(session, scene, "supported", "Irgendetwas Beta", {HOUSING: 0.9}, similarity=0.8)
    indexed_scored(session, scene, "middle", "Irgendetwas Gamma", {HOUSING: 0.5}, similarity=0.7)


def _weight(monkeypatch: pytest.MonkeyPatch, value: float) -> None:
    monkeypatch.setattr(settings, "search_confidence_weight", value)


def test_a_slightly_less_relevant_but_much_better_supported_candidate_can_outrank_a_barely_better_match(
    search_client: TestClient[Litestar], embedder: FakeQueryEmbedder, db_session: Session, search_scene: Scene
) -> None:
    _pool(db_session, search_scene)
    embedder.vectors = vector_for("kindergeld")

    items = search_client.get(URL, params=QUERY).json()["items"]

    assert [item["key"] for item in items] == ["supported", "middle", "best-match"]
    assert items[0]["score"] == pytest.approx(0.7 * 61 / 124 + 0.3 * 0.9, abs=1e-4)


@pytest.mark.parametrize(
    ("weight", "expected"),
    [
        (1.0, ["supported", "middle", "best-match"]),
        (0.0, ["best-match", "supported", "middle"]),
    ],
    ids=["weight 1 is confidence first", "weight 0 is pure relevance"],
)
def test_weight_one_orders_by_confidence_within_the_pool_and_weight_zero_by_relevance(
    search_client: TestClient[Litestar],
    embedder: FakeQueryEmbedder,
    db_session: Session,
    search_scene: Scene,
    monkeypatch: pytest.MonkeyPatch,
    weight: float,
    expected: list[str],
) -> None:
    _pool(db_session, search_scene)
    embedder.vectors = vector_for("kindergeld")
    _weight(monkeypatch, weight)

    assert keys(search_client.get(URL, params=QUERY)) == expected


def test_an_irrelevant_high_confidence_candidate_never_appears(
    search_client: TestClient[Litestar], embedder: FakeQueryEmbedder, db_session: Session, search_scene: Scene
) -> None:
    _pool(db_session, search_scene)
    indexed_scored(db_session, search_scene, "below-cut-off", "Irgendetwas Delta", {HOUSING: 1.0}, similarity=0.1)
    indexed_scored(db_session, search_scene, "unembedded", "Irgendetwas Epsilon", {HOUSING: 1.0}, similarity=None)
    embedder.vectors = vector_for("kindergeld")

    body = search_client.get(URL, params=QUERY).json()

    assert sorted(item["key"] for item in body["items"]) == ["best-match", "middle", "supported"]
    assert body["total"] == 3


def test_missing_confidence_counts_as_zero_and_never_errors(
    search_client: TestClient[Litestar], embedder: FakeQueryEmbedder, db_session: Session
) -> None:
    indexed(db_session, "Kindergeld Antrag", similarity=0.9)
    embedder.vectors = vector_for("kindergeld")

    response = search_client.get(URL, params=QUERY)

    [item] = response.json()["items"]
    assert (response.status_code, item["confidence"]) == (200, 0.0)
    assert item["score"] == pytest.approx(0.7)


def test_keyword_fallback_mode_still_orders_by_the_combined_score_with_single_leg_relevance(
    search_client: TestClient[Litestar], db_session: Session, search_scene: Scene
) -> None:
    indexed_scored(db_session, search_scene, "only", "Kindergeld Antrag", {HOUSING: 0.5}, similarity=None)

    body = search_client.get(URL, params=QUERY).json()

    assert body["search_mode"] == "keyword"
    assert body["items"][0]["score"] == pytest.approx(0.7 * 1.0 + 0.3 * 0.5)


def test_equal_scores_fall_back_to_the_deterministic_tie_break(
    search_client: TestClient[Litestar],
    db_session: Session,
    search_scene: Scene,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _weight(monkeypatch, 1.0)
    twins = [
        indexed_scored(db_session, search_scene, f"twin-{n}", "Kindergeld Antrag", {HOUSING: 0.5}, similarity=None)
        for n in range(4)
    ]

    first = keys(search_client.get(URL, params=QUERY))

    assert first == [twin.key for twin in sorted(twins, key=lambda twin: twin.id)]
    assert keys(search_client.get(URL, params=QUERY)) == first


def test_pages_are_stable(
    search_client: TestClient[Litestar], embedder: FakeQueryEmbedder, db_session: Session, search_scene: Scene
) -> None:
    for n in range(7):
        similarity = 0.9 - 0.05 * n
        indexed_scored(
            db_session, search_scene, f"c{n}", f"Irgendetwas {n}", {HOUSING: 0.3 + 0.1 * (n % 3)}, similarity=similarity
        )
    embedder.vectors = vector_for("kindergeld")

    whole = keys(search_client.get(URL, params={**QUERY, "limit": 50}))
    paged = [
        key
        for offset in (0, 3, 6)
        for key in keys(search_client.get(URL, params={**QUERY, "limit": 3, "offset": offset}))
    ]

    assert len(whole) == 7
    assert paged == whole


def test_browse_order_is_unchanged_whatever_the_weight(
    search_client: TestClient[Litestar], search_scene: Scene, monkeypatch: pytest.MonkeyPatch
) -> None:
    search_scene.scored("low", categories={HOUSING: 0.2})
    search_scene.scored("high", categories={HOUSING: 0.9})
    search_scene.candidate("unscored")
    seen = []
    for weight in (0.0, 0.3, 1.0):
        _weight(monkeypatch, weight)
        seen.append(search_client.get(URL).json()["items"])

    assert all([item["key"] for item in items] == ["high", "low", "unscored"] for items in seen)
    for items in seen:
        assert [item["score"] for item in items] == pytest.approx([item["confidence"] for item in items], abs=5e-5)


def test_the_legacy_title_match_scores_the_confidence(
    db_session: Session, search_scene: Scene, monkeypatch: pytest.MonkeyPatch, embedder: FakeQueryEmbedder
) -> None:
    indexed_scored(db_session, search_scene, "legacy", "Kindergeld Antrag", {HOUSING: 0.4}, similarity=None)
    with serve_with(monkeypatch, db_session, embedder, hybrid=False) as client:
        [item] = client.get(URL, params={"q": "kinder"}).json()["items"]

    assert item["score"] == pytest.approx(item["confidence"], abs=5e-5) == pytest.approx(0.4, abs=5e-5)


def test_each_card_carries_a_score_and_no_sort_by_yields_the_combined_order(
    search_client: TestClient[Litestar], embedder: FakeQueryEmbedder, db_session: Session, search_scene: Scene
) -> None:
    _pool(db_session, search_scene)
    embedder.vectors = vector_for("kindergeld")

    default = search_client.get(URL, params=QUERY).json()["items"]
    named = search_client.get(URL, params={**QUERY, "sort_by": "combined"}).json()["items"]

    assert [item["key"] for item in default] == [item["key"] for item in named]
    assert [item["score"] for item in default] == sorted((item["score"] for item in default), reverse=True)
    assert all(0.0 <= item["score"] <= 1.0 for item in default)


def test_an_explicit_sort_by_overrides_the_combined_order(
    search_client: TestClient[Litestar], embedder: FakeQueryEmbedder, db_session: Session, search_scene: Scene
) -> None:
    _pool(db_session, search_scene)
    embedder.vectors = vector_for("kindergeld")

    by_title = {**QUERY, "sort_by": "title", "sort_order": "asc"}
    by_confidence = {**QUERY, "sort_by": "confidence", "sort_order": "asc"}

    assert keys(search_client.get(URL, params=by_title)) == ["best-match", "supported", "middle"]
    assert keys(search_client.get(URL, params=by_confidence)) == ["best-match", "middle", "supported"]
