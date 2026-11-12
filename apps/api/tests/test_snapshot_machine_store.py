"""The snapshot object store (chapter 08): canonical JSON under the snapshot key, and unavailable without a store."""

from __future__ import annotations

import json
import uuid

import pytest
from app.features.translation.snapshot_store import SnapshotPayload, SnapshotStore
from app.schema.translation.snapshot_machine import RowBlock, TextBlock
from app.shared.object_store import InMemoryObjectStore, ObjectStoreUnavailableError

CATALOGUE = uuid.uuid5(uuid.NAMESPACE_URL, "redtape.test.snapshot-store")


def _payload(text: str = "Antrag") -> SnapshotPayload:
    return SnapshotPayload(
        locale="en",
        source_hash="h" * 64,
        engine="azure-translator",
        model=None,
        truncated=True,
        source_url="https://www.example.de/leistung",
        blocks=[TextBlock(kind="h1", text=text), RowBlock(kind="row", cells=["Frist", "4 Wochen"])],
    )


def test_the_object_is_sorted_key_json_under_the_snapshot_key() -> None:
    """Store · the object is canonical sorted-key JSON at translations/v1/snapshots/{catalogue}/{locale}/{sha}.json."""
    backend = InMemoryObjectStore()

    stored = SnapshotStore(backend).write(CATALOGUE, _payload())

    body = backend.get(stored.key)
    assert stored.key == f"translations/v1/snapshots/{CATALOGUE}/en/{stored.content_sha256}.json"
    assert (stored.size_bytes, backend.content_type(stored.key)) == (len(body), "application/json")
    assert body == json.dumps(json.loads(body), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    assert json.loads(body) == {
        "blocks": [{"kind": "h1", "text": "Antrag"}, {"cells": ["Frist", "4 Wochen"], "kind": "row"}],
        "engine": "azure-translator",
        "locale": "en",
        "model": None,
        "schema": 1,
        "source_hash": "h" * 64,
        "source_url": "https://www.example.de/leistung",
        "truncated": True,
        "unit": "snapshot",
    }


def test_equal_payloads_share_one_key_and_a_repeat_writes_one_object() -> None:
    """Store · equal payloads share one content hash and one key, so a repeat leaves a single object."""
    backend = InMemoryObjectStore()

    first = SnapshotStore(backend).write(CATALOGUE, _payload())
    second = SnapshotStore(backend).write(CATALOGUE, _payload())

    assert first.key == second.key
    assert backend.stored_keys() == [first.key]


def test_a_different_text_gets_a_different_key() -> None:
    """Store · a changed block changes the content hash, so the new object gets its own key."""
    backend = InMemoryObjectStore()

    first = SnapshotStore(backend).write(CATALOGUE, _payload("Antrag"))
    second = SnapshotStore(backend).write(CATALOGUE, _payload("Anträge"))

    assert first.key != second.key


def test_without_an_object_store_the_write_is_unavailable() -> None:
    """Store · with no object store configured, the store refuses at construction and nothing is written."""
    with pytest.raises(ObjectStoreUnavailableError):
        SnapshotStore(None)
