"""``GET /candidates/{id}/translation``: the stored text from the object store, with ETag revalidation."""

from __future__ import annotations

import logging
import uuid

import pytest
from app.models.discovery import DiscoveryCandidateMention
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy import select

from candidates_public_world import Scene
from translation_read_support import URL, StoreSlot, translated


def _text_url(owner_id: object) -> str:
    return f"{URL}/{owner_id}/translation"


def test_returns_the_stored_title_and_description_read_from_the_object_store_with_an_etag(
    read_client: TestClient[Litestar], search_scene: Scene, store_slot: StoreSlot
) -> None:
    owner = translated(search_scene, store_slot)

    response = read_client.get(_text_url(owner.id), params={"locale": "tr"})

    assert response.status_code == 200
    assert response.json() == {
        "locale": "tr",
        "title": "Çocuk parası başvurusu",
        "description": "Kimlik getirin",
        "source": "mt",
        "stale": False,
        "engine": "llm",
    }
    assert response.headers["etag"].startswith('"')
    assert store_slot.memory.reads == 1


def test_the_cache_headers_revalidate_and_are_not_immutable(
    read_client: TestClient[Litestar], search_scene: Scene, store_slot: StoreSlot
) -> None:
    owner = translated(search_scene, store_slot)

    headers = read_client.get(_text_url(owner.id), params={"locale": "tr"}).headers

    assert "immutable" not in headers["cache-control"]
    assert "must-revalidate" in headers["cache-control"]
    assert "max-age=" in headers["cache-control"]
    assert "accept-language" in headers["vary"].lower()


def test_a_matching_if_none_match_answers_304_and_performs_no_store_read(
    read_client: TestClient[Litestar], search_scene: Scene, store_slot: StoreSlot
) -> None:
    owner = translated(search_scene, store_slot)
    etag = read_client.get(_text_url(owner.id), params={"locale": "tr"}).headers["etag"]
    reads_after_first = store_slot.memory.reads

    revalidated = read_client.get(_text_url(owner.id), params={"locale": "tr"}, headers={"If-None-Match": etag})

    assert revalidated.status_code == 304
    assert revalidated.content == b""
    assert revalidated.headers["etag"] == etag
    assert store_slot.memory.reads == reads_after_first


def test_a_non_matching_if_none_match_reads_the_object_again(
    read_client: TestClient[Litestar], search_scene: Scene, store_slot: StoreSlot
) -> None:
    owner = translated(search_scene, store_slot)

    response = read_client.get(_text_url(owner.id), params={"locale": "tr"}, headers={"If-None-Match": '"other"'})

    assert response.status_code == 200
    assert store_slot.memory.reads == 1


def test_a_german_change_after_the_translation_changes_the_etag_and_flags_stale_instead_of_a_304(
    read_client: TestClient[Litestar], search_scene: Scene, store_slot: StoreSlot
) -> None:
    owner = translated(search_scene, store_slot)
    fresh = read_client.get(_text_url(owner.id), params={"locale": "tr"})
    search_scene.session.scalars(select(DiscoveryCandidateMention)).one().excerpt = "Neuer Hinweis"
    search_scene.session.flush()

    changed = read_client.get(
        _text_url(owner.id), params={"locale": "tr"}, headers={"If-None-Match": fresh.headers["etag"]}
    )

    assert changed.status_code == 200
    assert changed.json()["stale"] is True
    assert changed.headers["etag"] != fresh.headers["etag"]


def test_the_locale_defaults_to_the_request_locale_and_an_explicit_locale_wins(
    read_client: TestClient[Litestar], search_scene: Scene, store_slot: StoreSlot
) -> None:
    owner = translated(search_scene, store_slot)

    by_header = read_client.get(_text_url(owner.id), headers={"Accept-Language": "tr"})
    explicit = read_client.get(_text_url(owner.id), params={"locale": "tr"}, headers={"Accept-Language": "en"})

    assert by_header.json()["locale"] == explicit.json()["locale"] == "tr"


def test_a_locale_without_a_row_is_404_and_never_falls_back_to_another_locale(
    read_client: TestClient[Litestar], search_scene: Scene, store_slot: StoreSlot
) -> None:
    owner = translated(search_scene, store_slot, locale="tr")

    english = read_client.get(_text_url(owner.id), params={"locale": "en"})

    assert english.status_code == 404
    assert store_slot.memory.reads == 0


def test_404_without_a_row_for_de_and_for_an_unknown_candidate(
    read_client: TestClient[Litestar], search_scene: Scene, store_slot: StoreSlot
) -> None:
    bare = search_scene.candidate("bare")
    owner = translated(search_scene, store_slot)

    assert read_client.get(_text_url(bare.id), params={"locale": "tr"}).status_code == 404
    assert read_client.get(_text_url(owner.id), params={"locale": "de"}).status_code == 404
    assert read_client.get(_text_url(uuid.uuid4()), params={"locale": "tr"}).status_code == 404
    assert store_slot.memory.reads == 0


def test_503_when_object_storage_is_not_configured(
    read_client: TestClient[Litestar], search_scene: Scene, store_slot: StoreSlot
) -> None:
    owner = translated(search_scene, store_slot)
    store_slot.store = None

    assert read_client.get(_text_url(owner.id), params={"locale": "tr"}).status_code == 503


def test_404_and_a_logged_inconsistency_when_the_object_is_missing(
    read_client: TestClient[Litestar], search_scene: Scene, store_slot: StoreSlot, caplog: pytest.LogCaptureFixture
) -> None:
    owner = translated(search_scene, store_slot)
    for key in list(store_slot.memory.stored_keys()):
        store_slot.memory.delete(key)

    with caplog.at_level(logging.ERROR):
        response = read_client.get(_text_url(owner.id), params={"locale": "tr"})

    assert response.status_code == 404
    assert any(str(owner.id) in record.getMessage() for record in caplog.records)


def test_404_and_a_logged_inconsistency_when_the_object_is_not_a_translation(
    read_client: TestClient[Litestar], search_scene: Scene, store_slot: StoreSlot, caplog: pytest.LogCaptureFixture
) -> None:
    owner = translated(search_scene, store_slot)
    for key in list(store_slot.memory.stored_keys()):
        store_slot.memory.put(key, b"not json", "application/json")

    with caplog.at_level(logging.ERROR):
        response = read_client.get(_text_url(owner.id), params={"locale": "tr"})

    assert response.status_code == 404
    assert any(str(owner.id) in record.getMessage() for record in caplog.records)
