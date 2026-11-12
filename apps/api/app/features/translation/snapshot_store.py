"""``SnapshotStore``: translated page blocks as content-addressed JSON objects behind the ``ObjectStore`` port.

The key is ``translations/v1/snapshots/{catalogue_service_id}/{locale}/{content_sha256}.json``. Only the API writes it;
workers never hold the object store. The card store keeps its own key and its ``unit`` of ``card``.
"""

from __future__ import annotations

import hashlib
import json
from typing import Final, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.features.translation.store import KEY_PREFIX, StoredObject
from app.schema.translation.snapshot_machine import SnapshotBlock
from app.shared.object_store import ObjectStore
from app.shared.object_store.provider import require_store

CONTENT_TYPE: Final = "application/json"


class SnapshotPayload(BaseModel):
    """The body of one page translation: its blocks of text and where they came from, never the raw artifact."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    schema_version: Literal[1] = Field(default=1, alias="schema")
    unit: Literal["snapshot"] = "snapshot"
    locale: str
    source_hash: str
    engine: str
    model: str | None
    truncated: bool
    source_url: str
    blocks: list[SnapshotBlock]

    def to_canonical_json(self) -> bytes:
        """Return sorted-key, space-free UTF-8 JSON, so equal payloads share one content hash and one key."""
        fields = self.model_dump(mode="json", by_alias=True)
        return json.dumps(fields, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def snapshot_object_key(catalogue_id: UUID, locale: str, content_sha256: str) -> str:
    """Return the content-addressed key of a page translation into ``locale``."""
    return f"{KEY_PREFIX}/snapshots/{catalogue_id}/{locale}/{content_sha256}.json"


class SnapshotStore:
    """Write page translation objects; an unconfigured object store fails at construction."""

    def __init__(self, store: ObjectStore | None) -> None:
        """Wrap ``store``; raise :class:`ObjectStoreUnavailableError` when it is ``None`` (not configured)."""
        self._store = require_store(store)

    def write(self, catalogue_id: UUID, payload: SnapshotPayload) -> StoredObject:
        """Store ``payload`` under its content-addressed key and return the key, hash and size."""
        body = payload.to_canonical_json()
        digest = hashlib.sha256(body).hexdigest()
        key = snapshot_object_key(catalogue_id, payload.locale, digest)
        self._store.put(key, body, CONTENT_TYPE)
        return StoredObject(key=key, content_sha256=digest, size_bytes=len(body))
