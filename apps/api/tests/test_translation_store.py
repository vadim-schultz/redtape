"""TranslationStore: the content-addressed key layout, the canonical payload and the typed failures."""

from __future__ import annotations

import hashlib
import json
import uuid

import boto3
import pytest
from app.features.translation.store import (
    StoredObject,
    TranslationObjectInvalidError,
    TranslationObjectMissingError,
    TranslationPayload,
    TranslationStore,
)
from app.models.translation import TranslationSource
from app.shared.object_store import InMemoryObjectStore, ObjectStoreUnavailableError, S3Config, S3ObjectStore
from moto import mock_aws

CANDIDATE_ID = uuid.UUID("11111111-2222-3333-4444-555555555555")


def _payload(title: str = "Child benefit application", locale: str = "en") -> TranslationPayload:
    return TranslationPayload(
        locale=locale,
        title=title,
        description="Apply for child benefit at the family office § 62",
        source_hash="a" * 64,
        source=TranslationSource.MT,
        engine="llm",
        model="@cf/qwen/qwen3-30b-a3b-fp8",
    )


def _store() -> tuple[TranslationStore, InMemoryObjectStore]:
    backend = InMemoryObjectStore()
    return TranslationStore(backend), backend


def test_write_stores_the_payload_under_the_content_addressed_key_and_reads_it_back_identical() -> None:
    """store · writes a payload under the content-addressed key, reads it back identical, and the hash and size match."""
    store, backend = _store()
    payload = _payload()

    stored = store.write(CANDIDATE_ID, payload)

    raw = backend.get(stored.key)
    assert stored == StoredObject(
        key=f"translations/v1/{CANDIDATE_ID}/en/card/{hashlib.sha256(raw).hexdigest()}.json",
        content_sha256=hashlib.sha256(raw).hexdigest(),
        size_bytes=len(raw),
    )
    assert store.read(stored.key) == payload
    assert backend.content_type(stored.key) == "application/json"


def test_the_object_is_canonical_utf8_json_with_the_documented_fields() -> None:
    """store · the body is canonical UTF-8 JSON (sorted keys, no spaces, no escaping) so equal payloads share a key."""
    store, backend = _store()
    payload = _payload(title="Kinderzuschlag: Заява")

    first, second = store.write(CANDIDATE_ID, payload), store.write(CANDIDATE_ID, payload)

    body = backend.get(first.key)
    assert first == second
    assert backend.stored_keys() == [first.key]
    assert "Заява".encode() in body
    assert json.loads(body) == {
        "schema": 1,
        "unit": "card",
        "locale": "en",
        "title": "Kinderzuschlag: Заява",
        "description": "Apply for child benefit at the family office § 62",
        "source_hash": "a" * 64,
        "source": "mt",
        "engine": "llm",
        "model": "@cf/qwen/qwen3-30b-a3b-fp8",
    }
    assert body == json.dumps(json.loads(body), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def test_a_changed_translation_gets_a_new_key_and_the_old_object_stays_until_deleted() -> None:
    """store · content addressing: a re-translation writes a new object and delete removes only the old one."""
    store, backend = _store()
    old = store.write(CANDIDATE_ID, _payload("First"))
    new = store.write(CANDIDATE_ID, _payload("Second"))

    store.delete(old.key)

    assert old.key != new.key
    assert backend.stored_keys() == [new.key]


def test_reading_a_missing_object_raises_the_typed_error() -> None:
    """store · a missing object raises TranslationObjectMissingError naming the key."""
    store, _ = _store()

    with pytest.raises(TranslationObjectMissingError, match="translations/v1/gone"):
        store.read("translations/v1/gone")


def test_deleting_a_missing_key_is_a_no_op() -> None:
    """store · deleting a missing key does nothing and does not raise."""
    store, backend = _store()

    store.delete("translations/v1/gone")

    assert backend.stored_keys() == []


def test_an_unconfigured_store_raises_the_typed_unavailable_error() -> None:
    """store · without an object store the typed unavailable error is raised (HTTP 503 in routes)."""
    with pytest.raises(ObjectStoreUnavailableError):
        TranslationStore(None)


@pytest.mark.parametrize("body", [b"not json", b'{"schema": 2}', b'{"schema": 1, "unit": "card"}'])
def test_reading_a_corrupt_or_foreign_object_raises_the_invalid_error(body: bytes) -> None:
    """store · an unreadable body, a newer schema or missing fields raise TranslationObjectInvalidError."""
    store, backend = _store()
    backend.put("translations/v1/x", body, "application/json")

    with pytest.raises(TranslationObjectInvalidError):
        store.read("translations/v1/x")


def test_a_round_trip_through_the_real_s3_adapter_keeps_the_key_layout_hash_and_missing_semantics() -> None:
    """store · the same contract holds over the S3 adapter (moto stands in for R2): layout, hash, read, delete."""
    config = S3Config(
        endpoint_url=None,
        region="us-east-1",
        bucket="translations",
        access_key_id="k",
        secret_access_key="s",
        force_path_style=True,
    )
    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="translations")
        store = TranslationStore(S3ObjectStore.from_config(config))
        stored = store.write(CANDIDATE_ID, _payload())

        assert store.read(stored.key) == _payload()
        assert stored.key == f"translations/v1/{CANDIDATE_ID}/en/card/{stored.content_sha256}.json"
        store.delete(stored.key)
        store.delete(stored.key)
        with pytest.raises(TranslationObjectMissingError):
            store.read(stored.key)
