"""Serve the stored translation of a candidate: found by its index row, read from the object store on demand."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from app.features.candidates.etag import etag_matches, etag_of
from app.features.candidates.repository import TranslationIndexRepository, TranslationIndexRow
from app.features.translation.errors import TranslationNotFoundError
from app.features.translation.source import SourceRepository
from app.features.translation.store import (
    TranslationObjectInvalidError,
    TranslationObjectMissingError,
    TranslationPayload,
    TranslationStore,
)
from app.schema.candidate import CandidateTranslationText
from app.shared.object_store import ObjectStore

CACHE_CONTROL = "public, max-age=10800, must-revalidate"
"""A few hours, then revalidate: a re-translation replaces the content behind the same URL, so never ``immutable``."""

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class TranslationReply:
    """What to answer: the entity tag and the text (``None`` when the client copy is current)."""

    etag: str
    text: CandidateTranslationText | None


class TranslationReadService:
    """Look up the index row of a translation and read its object at most once per changed text."""

    def __init__(self, index: TranslationIndexRepository, sources: SourceRepository, store: ObjectStore | None) -> None:
        """Bind the service to the translation ``index``, the German ``sources`` and the metered, optional ``store``."""
        self._index = index
        self._sources = sources
        self._store = store

    def serve(self, candidate_id: UUID, locale: str, if_none_match: str | None) -> TranslationReply:
        """Return the reply for ``locale``; the store is not touched when ``if_none_match`` names the current text.

        Raises :class:`TranslationNotFoundError` without an index row or an object, and the object store's
        unavailable error (HTTP 503) when storage is not configured and the text must be read.
        """
        row = self._require_row(candidate_id, locale)
        stale = self._is_stale(row)
        etag = _etag(row, stale)
        if etag_matches(if_none_match, etag):
            return TranslationReply(etag, None)
        return TranslationReply(etag, _text(row, self._read(row), stale))

    def _require_row(self, candidate_id: UUID, locale: str) -> TranslationIndexRow:
        row = self._index.translation_of(candidate_id, locale)
        if row is None:
            raise TranslationNotFoundError()
        return row

    def _is_stale(self, row: TranslationIndexRow) -> bool:
        unit = self._sources.units_for([row.candidate_id]).get(row.candidate_id)
        return unit is None or unit.is_stale(row.source_hash)

    def _read(self, row: TranslationIndexRow) -> TranslationPayload:
        store = TranslationStore(self._store)
        try:
            return store.read(row.storage_key)
        except (TranslationObjectMissingError, TranslationObjectInvalidError) as err:
            logger.error(
                "translation index row has no readable object: candidate=%s locale=%s key=%s (%s)",
                row.candidate_id,
                row.locale,
                row.storage_key,
                err,
            )
            raise TranslationNotFoundError() from err


def _etag(row: TranslationIndexRow, stale: bool) -> str:
    """Derive the tag from the content hash, and from the stale flag too: it is in the body but not in the content."""
    return etag_of(f"{row.content_sha256}.stale" if stale else row.content_sha256)


def _text(row: TranslationIndexRow, payload: TranslationPayload, stale: bool) -> CandidateTranslationText:
    return CandidateTranslationText(
        locale=row.locale,
        title=payload.title,
        description=payload.description,
        source=row.source,
        stale=stale,
        engine=row.engine,
    )
