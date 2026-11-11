"""The translation summary on candidate cards and details: availability and provenance, never text."""

from __future__ import annotations

from app.models.discovery import DiscoveryCandidateMention
from app.models.translation import CandidateTranslation, TranslationSource
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from candidates_public_world import Scene
from translation_read_support import URL, StoreSlot, count_queries, translated

TURKISH = {"locale": "tr", "source": "mt", "stale": False}


def _item(body: dict, key: str) -> dict:
    return next(item for item in body["items"] if item["key"] == key)


def test_a_turkish_reader_gets_the_translation_summary_on_list_and_detail(
    read_client: TestClient[Litestar], search_scene: Scene, store_slot: StoreSlot
) -> None:
    owner = translated(search_scene, store_slot)

    listed = _item(read_client.get(URL, params={"locale": "tr"}).json(), owner.key)
    detail = read_client.get(f"{URL}/{owner.id}", params={"locale": "tr"}).json()

    assert listed["translation"] == TURKISH
    assert detail["translation"] == TURKISH
    assert "Çocuk" not in str(listed) and "Kimlik" not in str(listed)


def test_a_german_reader_gets_null_even_when_a_translation_is_stored(
    read_client: TestClient[Litestar], search_scene: Scene, store_slot: StoreSlot
) -> None:
    owner = translated(search_scene, store_slot)

    listed = _item(read_client.get(URL, params={"locale": "de"}).json(), owner.key)
    detail = read_client.get(f"{URL}/{owner.id}", params={"locale": "de"}).json()

    assert listed["translation"] is None
    assert detail["translation"] is None


def test_stale_is_true_after_the_german_description_changes(
    read_client: TestClient[Litestar], search_scene: Scene, store_slot: StoreSlot
) -> None:
    owner = translated(search_scene, store_slot)
    fresh = _item(read_client.get(URL, params={"locale": "tr"}).json(), owner.key)
    search_scene.session.scalars(select(DiscoveryCandidateMention)).one().excerpt = "Neuer Hinweis"
    search_scene.session.flush()

    changed = _item(read_client.get(URL, params={"locale": "tr"}).json(), owner.key)

    assert fresh["translation"]["stale"] is False
    assert changed["translation"] == {**TURKISH, "stale": True}


def test_stale_is_true_after_the_german_title_changes(
    read_client: TestClient[Litestar], search_scene: Scene, store_slot: StoreSlot
) -> None:
    owner = translated(search_scene, store_slot)
    owner.title_i18n = {"de": "Kindergeld beantragen"}
    search_scene.session.flush()

    detail = read_client.get(f"{URL}/{owner.id}", params={"locale": "tr"}).json()

    assert detail["translation"]["stale"] is True


def test_source_reflects_a_human_row(
    read_client: TestClient[Litestar], search_scene: Scene, store_slot: StoreSlot
) -> None:
    owner = translated(search_scene, store_slot)
    row = search_scene.session.scalars(select(CandidateTranslation)).one()
    row.source = TranslationSource.HUMAN
    search_scene.session.flush()

    detail = read_client.get(f"{URL}/{owner.id}", params={"locale": "tr"}).json()

    assert detail["translation"] == {**TURKISH, "source": "human"}


def test_no_translation_row_means_null_not_an_error(
    read_client: TestClient[Litestar], search_scene: Scene, store_slot: StoreSlot
) -> None:
    owner = search_scene.candidate("untranslated")

    listed = read_client.get(URL, params={"locale": "tr"})
    detail = read_client.get(f"{URL}/{owner.id}", params={"locale": "tr"})

    assert listed.status_code == detail.status_code == 200
    assert _item(listed.json(), owner.key)["translation"] is None
    assert detail.json()["translation"] is None
    assert store_slot.memory.reads == 0


def test_a_locale_without_a_stored_translation_never_falls_back_to_another_locale(
    read_client: TestClient[Litestar], search_scene: Scene, store_slot: StoreSlot
) -> None:
    owner = translated(search_scene, store_slot, locale="tr")

    english = read_client.get(f"{URL}/{owner.id}", params={"locale": "en"}).json()

    assert english["translation"] is None


def test_the_list_issues_a_constant_number_of_queries_and_makes_no_object_store_call(
    read_client: TestClient[Litestar], search_scene: Scene, store_slot: StoreSlot, db_session: Session
) -> None:
    for index in range(10):
        translated(search_scene, store_slot, f"doc-{index:02d}", title=f"Antrag {index:02d}")

    with count_queries(db_session) as small:
        small_page = read_client.get(URL, params={"locale": "tr", "limit": 2}).json()
    with count_queries(db_session) as large:
        large_page = read_client.get(URL, params={"locale": "tr", "limit": 10}).json()

    assert (len(small_page["items"]), len(large_page["items"])) == (2, 10)
    assert all(item["translation"] == TURKISH for item in large_page["items"])
    assert len(small) == len(large)
    assert store_slot.memory.reads == 0
