"""Serve the translated blocks of a candidate's document: the best mention's page, read from the object store on demand.

The read never translates, enqueues or writes (architecture invariant 1).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import NamedTuple
from uuid import UUID

from pydantic import ValidationError

from app.features.candidates.etag import etag_matches, etag_of
from app.features.candidates.service import BestMention, CandidateReadService
from app.features.discovery.artifact_read import ArtifactReadService, LatestSnapshot
from app.features.discovery.errors import CandidateNotFoundError, InvalidDiscoveryInputError
from app.features.translation.errors import DocumentUnavailableError
from app.features.translation.snapshot_repository import SnapshotRepository
from app.features.translation.snapshot_store import SnapshotPayload
from app.schema.candidate.document_translation import DocumentTranslationCode, DocumentTranslationRead
from app.schema.locale.keys import validate_locale_key
from app.shared.object_store import ObjectNotFoundError, ObjectStore
from app.shared.object_store.provider import require_store

logger = logging.getLogger(__name__)


class StoredPage(NamedTuple):
    """An index row that points at an object: the artifact it was checked against, the object's key and its hash."""

    artifact_sha256: str
    storage_key: str
    content_sha256: str


@dataclass(frozen=True, slots=True)
class DocumentReply:
    """What to answer: the entity tag and the blocks (``None`` when the client copy is current)."""

    etag: str
    body: DocumentTranslationRead | None


class DocumentTranslationReadService:
    """Resolve a candidate to its page and locale, and read the page's object at most once per changed text."""

    def __init__(
        self,
        candidates: CandidateReadService,
        artifacts: ArtifactReadService,
        index: SnapshotRepository,
        store: ObjectStore | None,
    ) -> None:
        """Bind the service to the candidate and artifact services, the snapshot index and the optional store."""
        self._candidates = candidates
        self._artifacts = artifacts
        self._index = index
        self._store = store

    def serve(self, candidate_id: UUID, locale: str, if_none_match: str | None) -> DocumentReply:
        """Return the reply for ``locale``; the store is not read when ``if_none_match`` names the current text.

        Raises :class:`DocumentUnavailableError` when there are no blocks, and the store's unavailable error (503)
        when the blocks must be read and storage is not configured.
        """
        code = _locale_code(locale)
        mention = self._best_mention(candidate_id)
        page = mention.catalogue_service_id
        latest = self._latest(page)
        stored = self._stored(page, code)
        stale = stored.artifact_sha256 != latest.sha256
        etag = _etag(stored.content_sha256, stale)
        if etag_matches(if_none_match, etag):
            return DocumentReply(etag, None)
        return DocumentReply(etag, _body(code, self._read(stored.storage_key), mention, stale))

    def _best_mention(self, candidate_id: UUID) -> BestMention:
        try:
            mention = self._candidates.best_mention(candidate_id)
        except CandidateNotFoundError as err:
            raise DocumentUnavailableError(DocumentTranslationCode.CANDIDATE_NOT_FOUND) from err
        if mention is None:
            raise DocumentUnavailableError(DocumentTranslationCode.NO_DOCUMENT)
        return mention

    def _latest(self, page: UUID) -> LatestSnapshot:
        latest = self._artifacts.latest_snapshot(page)
        if latest is None:
            raise DocumentUnavailableError(DocumentTranslationCode.NO_DOCUMENT)
        return latest

    def _stored(self, page: UUID, locale: str) -> StoredPage:
        row = self._index.index_row((page, locale))
        if row is not None and row.skipped_reason is not None:
            raise DocumentUnavailableError(DocumentTranslationCode.SKIPPED, row.skipped_reason)
        if row is None or row.storage_key is None or row.content_sha256 is None:
            raise DocumentUnavailableError(DocumentTranslationCode.TRANSLATION_PENDING)
        return StoredPage(row.artifact_sha256, row.storage_key, row.content_sha256)

    def _read(self, key: str) -> SnapshotPayload:
        store = require_store(self._store)
        try:
            return SnapshotPayload.model_validate_json(store.get(key))
        except (ObjectNotFoundError, ValidationError) as err:
            logger.error("snapshot index row has no readable object: key=%s (%s)", key, err)
            raise DocumentUnavailableError(DocumentTranslationCode.TRANSLATION_PENDING) from err


def _locale_code(locale: str) -> str:
    """Return the lower-cased supported locale code, or refuse the request with the existing locale error."""
    try:
        return validate_locale_key(locale)
    except ValueError as err:
        raise InvalidDiscoveryInputError(str(err)) from err


def _etag(content_sha256: str, stale: bool) -> str:
    """Derive the tag from the content hash, and from the stale flag too: it is in the body but not in the content."""
    return etag_of(f"{content_sha256}.stale" if stale else content_sha256)


def _body(locale: str, payload: SnapshotPayload, mention: BestMention, stale: bool) -> DocumentTranslationRead:
    return DocumentTranslationRead(
        locale=locale,
        source_url=mention.source_url,
        truncated=payload.truncated,
        stale=stale,
        blocks=payload.blocks,
    )
