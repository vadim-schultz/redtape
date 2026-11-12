"""``GET /candidates/{id}/document-translation``: the translated blocks of a candidate's best page (chapter 12)."""

from __future__ import annotations

import logging
import uuid
from typing import NamedTuple

import pytest
from app.features.translation.snapshot_store import SnapshotPayload, SnapshotStore
from app.models.discovery import CatalogueService, DiscoveryDocumentCandidate, DiscoveryMentionRole
from app.models.snapshot_translation import SnapshotTranslation, SnapshotTranslationTask
from app.models.translation import CandidateTranslation, TranslationTask
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from candidates_public_world import Scene
from embedding_support import NOW
from snapshot_machine_support import HASH_STORED, SHA_A, SHA_B, add_snapshot, skipped_row
from test_architecture import APP_ROOT, module_imports
from translation_read_support import URL, StoreSlot

PORTAL = "https://www.example.de/leistung/kindergeld"
BLOCKS: list[dict[str, object]] = [
    {"kind": "h1", "text": "Kindergeld beantragen"},
    {"kind": "p", "text": "Den Antrag stellen Sie online."},
    {"kind": "row", "cells": ["Frist", "4 Wochen"]},
]
OTHER_BLOCKS: list[dict[str, object]] = [{"kind": "p", "text": "Ein anderer Text."}]
FLAGGED: list[dict[str, object]] = [
    {"kind": "h1", "text": "Kindergeld beantragen"},
    {"kind": "p", "text": "Den Antrag stellen Sie online.", "untranslated": True},
    {"kind": "row", "cells": ["Frist", "4 Wochen"], "untranslated": True},
]


class Owned(NamedTuple):
    """A candidate and the procedure page its one mention cites."""

    candidate: DiscoveryDocumentCandidate
    page: CatalogueService


def _url(candidate: DiscoveryDocumentCandidate) -> str:
    return f"{URL}/{candidate.id}/document-translation"


def _page(scene: Scene, portal_url: str = PORTAL) -> CatalogueService:
    return scene.procedure("Leistung", portal_url=portal_url)


def _store_translation(
    session: Session, store: StoreSlot, page: CatalogueService, blocks: list[dict[str, object]] = BLOCKS
) -> SnapshotTranslation:
    """Write ``blocks`` of ``page`` in Turkish to the store and add the index row that points at them."""
    payload = SnapshotPayload(
        locale="tr",
        source_hash=HASH_STORED,
        engine="azure-translator",
        model=None,
        truncated=False,
        source_url=page.portal_url or PORTAL,
        blocks=blocks,
    )
    stored = SnapshotStore(store.memory).write(page.id, payload)
    row = SnapshotTranslation(
        catalogue_service_id=page.id,
        locale="tr",
        artifact_sha256=SHA_A,
        source_hash=HASH_STORED,
        engine="azure-translator",
        model=None,
        storage_key=stored.key,
        content_sha256=stored.content_sha256,
        size_bytes=stored.size_bytes,
        truncated=False,
        skipped_reason=None,
    )
    session.add(row)
    session.flush()
    return row


def _translated(
    scene: Scene, store: StoreSlot, key: str = "kindergeld", blocks: list[dict[str, object]] = BLOCKS
) -> Owned:
    """Add a candidate whose one mention is on a page with a snapshot, translated into Turkish with ``blocks``."""
    owner = scene.candidate(key, title={"de": "Kindergeldantrag"})
    page = _page(scene)
    scene.mention(owner, page, excerpt="Bitte Ausweis mitbringen")
    add_snapshot(scene.session, page, SHA_A)
    _store_translation(scene.session, store, page, blocks)
    return Owned(owner, page)


def _write_counts(session: Session) -> tuple[int, ...]:
    """Count the rows a write path could add: snapshot index rows and tasks, card index rows and tasks."""
    models = (SnapshotTranslation, SnapshotTranslationTask, TranslationTask, CandidateTranslation)
    return tuple(int(session.scalar(select(func.count()).select_from(model)) or 0) for model in models)


def test_a_translated_page_returns_its_blocks_in_the_requested_locale(
    read_client: TestClient[Litestar], search_scene: Scene, store_slot: StoreSlot
) -> None:
    owned = _translated(search_scene, store_slot)

    response = read_client.get(_url(owned.candidate), params={"locale": "tr"})

    assert response.status_code == 200
    assert response.json() == {
        "locale": "tr",
        "source_url": PORTAL,
        "truncated": False,
        "stale": False,
        "blocks": BLOCKS,
    }
    assert store_slot.memory.reads == 1


def test_a_block_that_kept_its_german_text_is_returned_with_its_untranslated_flag(
    read_client: TestClient[Litestar], search_scene: Scene, store_slot: StoreSlot
) -> None:
    """Read · each block carries its stored flag: true where the German text was kept, false elsewhere."""
    owned = _translated(search_scene, store_slot, blocks=FLAGGED)

    response = read_client.get(_url(owned.candidate), params={"locale": "tr"})

    assert response.status_code == 200
    assert response.json()["blocks"] == [
        {"kind": "h1", "text": "Kindergeld beantragen", "untranslated": False},
        {"kind": "p", "text": "Den Antrag stellen Sie online.", "untranslated": True},
        {"kind": "row", "cells": ["Frist", "4 Wochen"], "untranslated": True},
    ]


def test_the_etag_is_the_content_hash_and_the_cache_headers_revalidate(
    read_client: TestClient[Litestar], search_scene: Scene, store_slot: StoreSlot
) -> None:
    owned = _translated(search_scene, store_slot)
    row = search_scene.session.scalars(select(SnapshotTranslation)).one()

    headers = read_client.get(_url(owned.candidate), params={"locale": "tr"}).headers

    assert headers["etag"] == f'"{row.content_sha256}"'
    assert "must-revalidate" in headers["cache-control"]
    assert "immutable" not in headers["cache-control"]


def test_a_second_request_with_a_matching_if_none_match_gets_304_and_reads_no_object(
    read_client: TestClient[Litestar], search_scene: Scene, store_slot: StoreSlot
) -> None:
    owned = _translated(search_scene, store_slot)
    etag = read_client.get(_url(owned.candidate), params={"locale": "tr"}).headers["etag"]
    reads_after_first = store_slot.memory.reads

    revalidated = read_client.get(_url(owned.candidate), params={"locale": "tr"}, headers={"If-None-Match": etag})

    assert revalidated.status_code == 304
    assert revalidated.content == b""
    assert revalidated.headers["etag"] == etag
    assert store_slot.memory.reads == reads_after_first


def test_the_best_mention_picks_the_page_in_the_order_the_card_excerpt_uses(
    read_client: TestClient[Litestar], search_scene: Scene, store_slot: StoreSlot
) -> None:
    owner = search_scene.candidate("kindergeld", title={"de": "Kindergeldantrag"})
    form = _page(search_scene, "https://www.example.de/formular")
    required = _page(search_scene, PORTAL)
    search_scene.mention(owner, form, role=DiscoveryMentionRole.FORM, excerpt="Formular ausfüllen")
    search_scene.mention(owner, required, role=DiscoveryMentionRole.REQUIRED, excerpt="Früher Hinweis")
    for page in (form, required):
        add_snapshot(search_scene.session, page, SHA_A)
    _store_translation(search_scene.session, store_slot, form, OTHER_BLOCKS)
    _store_translation(search_scene.session, store_slot, required)

    body = read_client.get(_url(owner), params={"locale": "tr"}).json()
    card = read_client.get(f"{URL}/{owner.id}", params={"locale": "tr"}).json()

    assert card["description"] == "Früher Hinweis"
    assert (body["source_url"], body["blocks"]) == (PORTAL, BLOCKS)


def test_stale_is_true_when_the_latest_snapshot_sha_differs_from_the_stored_one(
    read_client: TestClient[Litestar], search_scene: Scene, store_slot: StoreSlot
) -> None:
    owned = _translated(search_scene, store_slot)
    fresh = read_client.get(_url(owned.candidate), params={"locale": "tr"}).json()
    add_snapshot(search_scene.session, owned.page, SHA_B, fetched_at=NOW)

    stale = read_client.get(_url(owned.candidate), params={"locale": "tr"}).json()

    assert fresh["stale"] is False
    assert stale["stale"] is True
    assert stale["blocks"] == BLOCKS


def test_a_candidate_with_no_snapshot_answers_404_no_document(
    read_client: TestClient[Litestar], search_scene: Scene, store_slot: StoreSlot
) -> None:
    unsnapshotted = search_scene.candidate("ohne-seite")
    search_scene.mention(unsnapshotted, _page(search_scene))
    without_mention = search_scene.candidate("ohne-mention")

    first = read_client.get(_url(unsnapshotted), params={"locale": "tr"})
    second = read_client.get(_url(without_mention), params={"locale": "tr"})

    assert (first.status_code, first.json()["code"]) == (404, "no_document")
    assert (second.status_code, second.json()["code"]) == (404, "no_document")
    assert store_slot.memory.reads == 0


def test_a_pending_translation_answers_404_translation_pending(
    read_client: TestClient[Litestar], search_scene: Scene, store_slot: StoreSlot
) -> None:
    owner = search_scene.candidate("wartend")
    page = _page(search_scene)
    search_scene.mention(owner, page)
    add_snapshot(search_scene.session, page, SHA_A)

    response = read_client.get(_url(owner), params={"locale": "tr"})

    assert response.status_code == 404
    assert response.json()["code"] == "translation_pending"
    assert store_slot.memory.reads == 0


def test_a_skipped_page_answers_404_skipped_with_the_reason(
    read_client: TestClient[Litestar], search_scene: Scene, store_slot: StoreSlot
) -> None:
    owner = search_scene.candidate("leer")
    page = _page(search_scene)
    search_scene.mention(owner, page)
    add_snapshot(search_scene.session, page, SHA_A)
    skipped_row(search_scene.session, page, "tr", "too_short")

    response = read_client.get(_url(owner), params={"locale": "tr"})

    assert response.status_code == 404
    assert response.json() == {"code": "skipped", "reason": "too_short"}
    assert store_slot.memory.reads == 0


def test_an_unconfigured_object_store_answers_503(
    read_client: TestClient[Litestar], search_scene: Scene, store_slot: StoreSlot
) -> None:
    owned = _translated(search_scene, store_slot)
    store_slot.store = None

    assert read_client.get(_url(owned.candidate), params={"locale": "tr"}).status_code == 503


def test_an_object_missing_after_a_replacement_race_answers_translation_pending_and_does_not_raise(
    read_client: TestClient[Litestar], search_scene: Scene, store_slot: StoreSlot, caplog: pytest.LogCaptureFixture
) -> None:
    owned = _translated(search_scene, store_slot)
    row = search_scene.session.scalars(select(SnapshotTranslation)).one()
    assert row.storage_key is not None
    store_slot.memory.delete(row.storage_key)

    with caplog.at_level(logging.ERROR):
        response = read_client.get(_url(owned.candidate), params={"locale": "tr"})

    assert response.status_code == 404
    assert response.json()["code"] == "translation_pending"
    assert any(record.levelno >= logging.ERROR for record in caplog.records)


def test_an_unknown_locale_is_refused_with_the_existing_locale_error(
    read_client: TestClient[Litestar], search_scene: Scene, store_slot: StoreSlot
) -> None:
    owned = _translated(search_scene, store_slot)

    response = read_client.get(_url(owned.candidate), params={"locale": "fr"})

    assert response.status_code == 422
    assert "unsupported locale code: 'fr'" in response.text
    assert store_slot.memory.reads == 0


def test_an_unknown_candidate_answers_404_candidate_not_found(
    read_client: TestClient[Litestar], search_scene: Scene, store_slot: StoreSlot
) -> None:
    response = read_client.get(f"{URL}/{uuid.uuid4()}/document-translation", params={"locale": "tr"})

    assert response.status_code == 404
    assert response.json()["code"] == "candidate_not_found"


def test_the_route_writes_nothing_and_enqueues_nothing(
    read_client: TestClient[Litestar], search_scene: Scene, store_slot: StoreSlot, db_session: Session
) -> None:
    owned = _translated(search_scene, store_slot)
    db_session.flush()
    before = _write_counts(db_session)

    response = read_client.get(_url(owned.candidate), params={"locale": "tr"})

    assert response.status_code == 200
    assert _write_counts(db_session) == before == (1, 0, 0, 0)
    assert not db_session.new and not db_session.dirty and not db_session.deleted


def test_the_read_service_reaches_no_repository_of_another_feature() -> None:
    """Layering · the read service calls other features through their services, never their repositories."""
    path = APP_ROOT / "features" / "translation" / "document_read_service.py"
    offenders = [
        dotted
        for _lineno, dotted in module_imports(path)
        if dotted.startswith("app.features.")
        and ".repository" in dotted
        and not dotted.startswith("app.features.translation.")
    ]

    assert offenders == []
