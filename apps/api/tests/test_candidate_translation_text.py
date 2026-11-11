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
from translation_read_support import URL, StoreSlot, reader, scene, slot, translated  # noqa: F401


def _text_url(owner_id: object) -> str:
    return f"{URL}/{owner_id}/translation"


def test_returns_the_stored_title_and_description_read_from_the_object_store_with_an_etag(
    reader: TestClient[Litestar], scene: Scene, slot: StoreSlot
) -> None:
    owner = translated(scene, slot)

    response = reader.get(_text_url(owner.id), params={"locale": "tr"})

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
    assert slot.memory.reads == 1


def test_the_cache_headers_revalidate_and_are_not_immutable(
    reader: TestClient[Litestar], scene: Scene, slot: StoreSlot
) -> None:
    owner = translated(scene, slot)

    headers = reader.get(_text_url(owner.id), params={"locale": "tr"}).headers

    assert "immutable" not in headers["cache-control"]
    assert "must-revalidate" in headers["cache-control"]
    assert "max-age=" in headers["cache-control"]
    assert "accept-language" in headers["vary"].lower()


def test_a_matching_if_none_match_answers_304_and_performs_no_store_read(
    reader: TestClient[Litestar], scene: Scene, slot: StoreSlot
) -> None:
    owner = translated(scene, slot)
    etag = reader.get(_text_url(owner.id), params={"locale": "tr"}).headers["etag"]
    reads_after_first = slot.memory.reads

    revalidated = reader.get(_text_url(owner.id), params={"locale": "tr"}, headers={"If-None-Match": etag})

    assert revalidated.status_code == 304
    assert revalidated.content == b""
    assert revalidated.headers["etag"] == etag
    assert slot.memory.reads == reads_after_first


def test_a_non_matching_if_none_match_reads_the_object_again(
    reader: TestClient[Litestar], scene: Scene, slot: StoreSlot
) -> None:
    owner = translated(scene, slot)

    response = reader.get(_text_url(owner.id), params={"locale": "tr"}, headers={"If-None-Match": '"other"'})

    assert response.status_code == 200
    assert slot.memory.reads == 1


def test_a_german_change_after_the_translation_changes_the_etag_and_flags_stale_instead_of_a_304(
    reader: TestClient[Litestar], scene: Scene, slot: StoreSlot
) -> None:
    owner = translated(scene, slot)
    fresh = reader.get(_text_url(owner.id), params={"locale": "tr"})
    scene.session.scalars(select(DiscoveryCandidateMention)).one().excerpt = "Neuer Hinweis"
    scene.session.flush()

    changed = reader.get(_text_url(owner.id), params={"locale": "tr"}, headers={"If-None-Match": fresh.headers["etag"]})

    assert changed.status_code == 200
    assert changed.json()["stale"] is True
    assert changed.headers["etag"] != fresh.headers["etag"]


def test_the_locale_defaults_to_the_request_locale_and_an_explicit_locale_wins(
    reader: TestClient[Litestar], scene: Scene, slot: StoreSlot
) -> None:
    owner = translated(scene, slot)

    by_header = reader.get(_text_url(owner.id), headers={"Accept-Language": "tr"})
    explicit = reader.get(_text_url(owner.id), params={"locale": "tr"}, headers={"Accept-Language": "en"})

    assert by_header.json()["locale"] == explicit.json()["locale"] == "tr"


def test_a_locale_without_a_row_is_404_and_never_falls_back_to_another_locale(
    reader: TestClient[Litestar], scene: Scene, slot: StoreSlot
) -> None:
    owner = translated(scene, slot, locale="tr")

    english = reader.get(_text_url(owner.id), params={"locale": "en"})

    assert english.status_code == 404
    assert slot.memory.reads == 0


def test_404_without_a_row_for_de_and_for_an_unknown_candidate(
    reader: TestClient[Litestar], scene: Scene, slot: StoreSlot
) -> None:
    bare = scene.candidate("bare")
    owner = translated(scene, slot)

    assert reader.get(_text_url(bare.id), params={"locale": "tr"}).status_code == 404
    assert reader.get(_text_url(owner.id), params={"locale": "de"}).status_code == 404
    assert reader.get(_text_url(uuid.uuid4()), params={"locale": "tr"}).status_code == 404
    assert slot.memory.reads == 0


def test_503_when_object_storage_is_not_configured(
    reader: TestClient[Litestar], scene: Scene, slot: StoreSlot
) -> None:
    owner = translated(scene, slot)
    slot.store = None

    assert reader.get(_text_url(owner.id), params={"locale": "tr"}).status_code == 503


def test_404_and_a_logged_inconsistency_when_the_object_is_missing(
    reader: TestClient[Litestar], scene: Scene, slot: StoreSlot, caplog: pytest.LogCaptureFixture
) -> None:
    owner = translated(scene, slot)
    for key in list(slot.memory.stored_keys()):
        slot.memory.delete(key)

    with caplog.at_level(logging.ERROR):
        response = reader.get(_text_url(owner.id), params={"locale": "tr"})

    assert response.status_code == 404
    assert any(str(owner.id) in record.getMessage() for record in caplog.records)


def test_404_and_a_logged_inconsistency_when_the_object_is_not_a_translation(
    reader: TestClient[Litestar], scene: Scene, slot: StoreSlot, caplog: pytest.LogCaptureFixture
) -> None:
    owner = translated(scene, slot)
    for key in list(slot.memory.stored_keys()):
        slot.memory.put(key, b"not json", "application/json")

    with caplog.at_level(logging.ERROR):
        response = reader.get(_text_url(owner.id), params={"locale": "tr"})

    assert response.status_code == 404
    assert any(str(owner.id) in record.getMessage() for record in caplog.records)
