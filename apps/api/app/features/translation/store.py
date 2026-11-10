"""``TranslationStore``: translated card text as content-addressed JSON objects behind the ``ObjectStore`` port.

The key is ``translations/v1/{candidate_id}/{locale}/{unit}/{content_sha256}.json``. ``unit`` is ``card`` today and is
the seam for full-document units (open seam O16). Writes happen only in the API; the database keeps the index row.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.models.translation import TranslationSource
from app.shared.object_store import ObjectNotFoundError, ObjectStore
from app.shared.object_store.provider import require_store

KEY_PREFIX: Final = "translations/v1"
CONTENT_TYPE: Final = "application/json"


class TranslationObjectMissingError(Exception):
    """The index row names an object that the store does not have."""

    def __init__(self, key: str) -> None:
        """Build the error naming the missing ``key``."""
        super().__init__(f"Translation object not found: {key}")


class TranslationObjectInvalidError(Exception):
    """The object exists but is not a translation payload this code understands (corrupt or a newer schema)."""


class TranslationPayload(BaseModel):
    """The body of one translation object: the translated title and description and where they came from."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    schema_version: Literal[1] = Field(default=1, alias="schema")
    unit: Literal["card"] = "card"
    locale: str
    title: str
    description: str
    source_hash: str
    source: TranslationSource
    engine: str
    model: str | None

    def to_canonical_json(self) -> bytes:
        """Return sorted-key, space-free UTF-8 JSON, so equal payloads share one content hash and one key."""
        fields = self.model_dump(mode="json", by_alias=True)
        return json.dumps(fields, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()

    @classmethod
    def from_json(cls, body: bytes) -> TranslationPayload:
        """Parse an object body; raise :class:`TranslationObjectInvalidError` when it is not a valid payload."""
        try:
            return cls.model_validate_json(body)
        except ValidationError as err:
            raise TranslationObjectInvalidError("Translation object is not a valid payload") from err


@dataclass(frozen=True, slots=True)
class StoredObject:
    """What a write produced: the object key, the SHA-256 of its bytes and their size, as the index row records them."""

    key: str
    content_sha256: str
    size_bytes: int


def object_key(candidate_id: uuid.UUID, payload: TranslationPayload, content_sha256: str) -> str:
    """Return the content-addressed key of ``payload`` (whose bytes hash to ``content_sha256``) for ``candidate_id``."""
    return f"{KEY_PREFIX}/{candidate_id}/{payload.locale}/{payload.unit}/{content_sha256}.json"


class TranslationStore:
    """Write, read and delete translation objects; an unconfigured object store fails at construction."""

    def __init__(self, store: ObjectStore | None) -> None:
        """Wrap ``store``; raise :class:`ObjectStoreUnavailableError` when it is ``None`` (not configured)."""
        self._store = require_store(store)

    def write(self, candidate_id: uuid.UUID, payload: TranslationPayload) -> StoredObject:
        """Store ``payload`` under its content-addressed key and return the key, hash and size."""
        body = payload.to_canonical_json()
        digest = hashlib.sha256(body).hexdigest()
        key = object_key(candidate_id, payload, digest)
        self._store.put(key, body, CONTENT_TYPE)
        return StoredObject(key=key, content_sha256=digest, size_bytes=len(body))

    def read(self, key: str) -> TranslationPayload:
        """Return the payload at ``key``; raise the typed missing or invalid error when it cannot be read."""
        try:
            body = self._store.get(key)
        except ObjectNotFoundError as err:
            raise TranslationObjectMissingError(key) from err
        return TranslationPayload.from_json(body)

    def delete(self, key: str) -> None:
        """Remove the object at ``key``; a missing key is a no-op."""
        self._store.delete(key)
