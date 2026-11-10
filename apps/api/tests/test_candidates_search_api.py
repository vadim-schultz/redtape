"""``GET /api/v1/candidates?q=`` with hybrid retrieval: fusion, filters, locales, ordering and the legacy path."""

from __future__ import annotations

import pytest
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy.orm import Session

from candidates_public_world import HOUSING, MOVING, Scene
from query_embedder_support import FakeQueryEmbedder
from search_api_fixtures import URL, keys, serve_with, vector_for
from search_query_world import add_embedding, add_text, at_similarity, indexed
from search_support import search_service


def indexed_scored(
    session: Session,
    search_scene: Scene,
    key: str,
    title: str,
    categories: dict[str, float],
    *,
    similarity: float | None,
) -> None:
    """Add a categorised candidate with a search text and, when ``similarity`` is given, an embedding."""
    candidate = search_scene.scored(key, categories=categories, title={"de": title})
    search_service(session).refresh(candidate.id)
    if similarity is not None:
        add_embedding(session, candidate, at_similarity(similarity))


def test_a_german_phrase_and_a_turkish_paraphrase_both_find_the_candidate(
    search_client: TestClient[Litestar], embedder: FakeQueryEmbedder, db_session: Session
) -> None:
    indexed(db_session, "Kindergeldantrag", "Antrag auf Kindergeld stellen", similarity=0.9)
    indexed(db_session, "Wohnungsgeberbestaetigung", "Vermieter bestaetigt den Einzug", similarity=0.1)
    embedder.vectors = vector_for("kindergeld", "çocuk yardımı")

    german = search_client.get(URL, params={"q": "Kindergeld"}).json()
    turkish = search_client.get(URL, params={"q": "Çocuk yardımı"}).json()

    assert [item["title"] for item in german["items"]] == ["Kindergeldantrag"]
    assert [item["title"] for item in turkish["items"]] == ["Kindergeldantrag"]
    assert german["search_mode"] == turkish["search_mode"] == "hybrid"
    assert turkish["items"][0]["similarity"] is not None


def test_a_query_nothing_is_similar_to_returns_an_empty_hybrid_list(
    search_client: TestClient[Litestar], embedder: FakeQueryEmbedder, db_session: Session
) -> None:
    indexed(db_session, "Kindergeldantrag", similarity=0.05)
    embedder.vectors = vector_for("qzxwv")

    body = search_client.get(URL, params={"q": "qzxwv"}).json()

    assert (body["items"], body["total"], body["search_mode"]) == ([], 0, "hybrid")


def test_similarity_is_rescaled_to_the_cut_off_and_null_for_keyword_only_matches(
    search_client: TestClient[Litestar], embedder: FakeQueryEmbedder, db_session: Session
) -> None:
    indexed(db_session, "Semantic only", similarity=0.65)
    indexed(db_session, "Kindergeld wortgleich")
    embedder.vectors = vector_for("kindergeld")

    items = {item["title"]: item for item in search_client.get(URL, params={"q": "kindergeld"}).json()["items"]}

    assert items["Semantic only"]["similarity"] == pytest.approx((0.65 - 0.3) / (1 - 0.3), abs=5e-3)
    assert items["Kindergeld wortgleich"]["similarity"] is None


def test_the_better_match_ranks_first_and_total_is_the_pool_size(
    search_client: TestClient[Litestar], embedder: FakeQueryEmbedder, db_session: Session
) -> None:
    indexed(db_session, "Kindergeld Antrag", similarity=0.9)
    indexed(db_session, "Kindergeld Bescheid")
    indexed(db_session, "Irgendetwas", similarity=0.8)
    embedder.vectors = vector_for("kindergeld")

    body = search_client.get(URL, params={"q": "kindergeld", "limit": 1}).json()
    second = search_client.get(URL, params={"q": "kindergeld", "limit": 1, "offset": 1}).json()

    assert body["items"][0]["title"] == "Kindergeld Antrag"
    assert second["items"][0]["title"] != "Kindergeld Antrag"
    assert body["total"] == second["total"] == 3


def test_the_category_filter_applies_to_both_legs_and_a_root_includes_descendants(
    search_client: TestClient[Litestar], embedder: FakeQueryEmbedder, db_session: Session, search_scene: Scene
) -> None:
    indexed_scored(db_session, search_scene, "in-child", "Kindergeld Wohnsitz", {MOVING: 0.8}, similarity=0.9)
    indexed_scored(db_session, search_scene, "in-root", "Kindergeld Miete", {HOUSING: 0.7}, similarity=0.85)
    indexed_scored(db_session, search_scene, "elsewhere", "Kindergeld Rente", {"retirement": 0.9}, similarity=0.95)
    indexed_scored(db_session, search_scene, "vector-elsewhere", "Rentenauskunft", {"retirement": 0.9}, similarity=0.99)
    indexed_scored(db_session, search_scene, "vector-child", "Umzugsmitteilung", {MOVING: 0.9}, similarity=0.7)
    embedder.vectors = vector_for("kindergeld")

    response = search_client.get(URL, params={"q": "kindergeld", "filter[category]": HOUSING})

    assert sorted(keys(response)) == ["in-child", "in-root", "vector-child"]
    assert response.json()["total"] == 3


def test_a_turkish_query_matches_turkish_rows_through_turkish_and_german_rows_through_german(
    embedder: FakeQueryEmbedder, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.lifespan._load_enabled_locales", lambda: {"de", "en", "tr"})
    turkish = indexed(db_session, "Meldebescheinigung")
    add_text(db_session, turkish, "tr", "Kimlikler ve evrak")
    indexed(db_session, "Wohnungsanmeldung")

    with serve_with(monkeypatch, db_session, embedder) as client:
        by_turkish = client.get(URL, params={"q": "kimlik", "locale": "tr"}).json()
        by_german = client.get(URL, params={"q": "wohnungsanmeldungen", "locale": "tr"}).json()
        unserved = client.get(URL, params={"q": "kimlik", "locale": "de"}).json()

    assert [item["title"] for item in by_turkish["items"]] == ["Meldebescheinigung"]
    assert [item["title"] for item in by_german["items"]] == ["Wohnungsanmeldung"]
    assert unserved["items"] == []
    assert by_turkish["search_mode"] == "keyword"


def test_no_q_is_unchanged_browse(
    search_client: TestClient[Litestar], embedder: FakeQueryEmbedder, search_scene: Scene
) -> None:
    search_scene.scored("low", categories={HOUSING: 0.2})
    search_scene.scored("high", categories={HOUSING: 0.9})

    body = search_client.get(URL).json()

    assert [item["key"] for item in body["items"]] == ["high", "low"]
    assert body["search_mode"] == "browse"
    assert all(item["similarity"] is None for item in body["items"])
    assert embedder.calls == []


def test_a_blank_q_is_browse_and_embeds_nothing(
    search_client: TestClient[Litestar], embedder: FakeQueryEmbedder, search_scene: Scene
) -> None:
    search_scene.candidate("only")

    body = search_client.get(URL, params={"q": "   "}).json()

    assert (body["search_mode"], body["total"]) == ("browse", 1)
    assert embedder.calls == []


def test_flag_off_keeps_the_legacy_title_matching(
    db_session: Session, monkeypatch: pytest.MonkeyPatch, embedder: FakeQueryEmbedder
) -> None:
    indexed(db_session, "Kindergeldantrag")
    indexed(db_session, "Nachweis", "Bitte Kindergeld beantragen")
    with serve_with(monkeypatch, db_session, embedder, hybrid=False) as client:
        body = client.get(URL, params={"q": "kinder"}).json()
        by_text = client.get(URL, params={"q": "beantragen"}).json()

    assert [item["title"] for item in body["items"]] == ["Kindergeldantrag"]
    assert body["search_mode"] == "keyword"
    assert by_text["items"] == []
    assert embedder.calls == []


def test_an_explicit_sort_by_overrides_the_fused_order(
    search_client: TestClient[Litestar], embedder: FakeQueryEmbedder, db_session: Session
) -> None:
    indexed(db_session, "Kindergeld Zeta", similarity=0.95)
    indexed(db_session, "Alpha", similarity=0.5)
    embedder.vectors = vector_for("kindergeld")

    fused = search_client.get(URL, params={"q": "kindergeld"}).json()["items"]
    titled = search_client.get(URL, params={"q": "kindergeld", "sort_by": "title", "sort_order": "asc"}).json()["items"]

    assert [item["title"] for item in fused] == ["Kindergeld Zeta", "Alpha"]
    assert [item["title"] for item in titled] == ["Alpha", "Kindergeld Zeta"]


def test_a_query_over_the_length_cap_answers_422(search_client: TestClient[Litestar]) -> None:
    assert search_client.get(URL, params={"q": "a" * 201}).status_code == 422


def test_the_detail_card_has_no_similarity(search_client: TestClient[Litestar], search_scene: Scene) -> None:
    owner = search_scene.candidate("detail")

    assert search_client.get(f"{URL}/{owner.id}").json()["similarity"] is None
