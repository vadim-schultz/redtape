"""``GET /api/v1/candidates`` without ``sort_by`` returns the combined-score order, one default for every client."""

from __future__ import annotations

from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy.orm import Session

from candidates_public_world import HOUSING, Scene
from query_embedder_support import FakeQueryEmbedder
from search_api_fixtures import URL, indexed_scored, keys, vector_for

QUERY = {"q": "kindergeld"}


def _pool(session: Session, scene: Scene) -> None:
    """Three vector-only matches: ``best-match`` is the closest, ``supported`` the best evidenced."""
    indexed_scored(session, scene, "best-match", "Irgendetwas Alpha", {HOUSING: 0.1}, similarity=0.9)
    indexed_scored(session, scene, "supported", "Irgendetwas Beta", {HOUSING: 0.9}, similarity=0.8)
    indexed_scored(session, scene, "middle", "Irgendetwas Gamma", {HOUSING: 0.5}, similarity=0.7)


def test_no_sort_by_with_a_query_orders_by_relevance_blended_with_confidence(
    search_client: TestClient[Litestar], embedder: FakeQueryEmbedder, db_session: Session, search_scene: Scene
) -> None:
    _pool(db_session, search_scene)
    embedder.vectors = vector_for("kindergeld")

    unsorted = keys(search_client.get(URL, params=QUERY))
    named = keys(search_client.get(URL, params={**QUERY, "sort_by": "combined"}))

    assert unsorted == named == ["supported", "middle", "best-match"]


def test_no_sort_by_without_a_query_orders_by_confidence_alone(
    search_client: TestClient[Litestar], search_scene: Scene
) -> None:
    search_scene.scored("low", categories={HOUSING: 0.2})
    search_scene.scored("high", categories={HOUSING: 0.9})
    search_scene.scored("mid", categories={HOUSING: 0.5})

    unsorted = keys(search_client.get(URL))
    named = keys(search_client.get(URL, params={"sort_by": "combined"}))

    assert unsorted == named == ["high", "mid", "low"]


def test_the_default_is_neither_title_order_nor_completeness_order(
    search_client: TestClient[Litestar], search_scene: Scene
) -> None:
    search_scene.complete_candidate("a-complete")
    search_scene.scored("z-sure", categories={HOUSING: 0.95})

    unsorted = keys(search_client.get(URL))
    by_completeness = keys(search_client.get(URL, params={"sort_by": "completeness", "sort_order": "desc"}))
    by_title = keys(search_client.get(URL, params={"sort_by": "title", "sort_order": "asc"}))

    assert unsorted[0] == "z-sure"
    assert by_completeness[0] == "a-complete"
    assert by_title[0] == "a-complete"


def test_a_sort_order_without_sort_by_is_rejected_instead_of_changing_the_default(
    search_client: TestClient[Litestar], search_scene: Scene
) -> None:
    search_scene.scored("only", categories={HOUSING: 0.5})

    assert search_client.get(URL, params={"sort_order": "asc"}).status_code == 422
