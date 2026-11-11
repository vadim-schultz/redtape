"""The index rows of stored translations: which candidates have one for a locale, and which object holds the text."""

from __future__ import annotations

from collections.abc import Sequence
from typing import NamedTuple
from uuid import UUID

from sqlalchemy import select

from app.features.discovery.repository.base import SessionRepository
from app.models.translation import CandidateTranslation as Row
from app.models.translation import TranslationSource
from app.shared.locale import DEFAULT_LOCALE


class TranslationIndexRow(NamedTuple):
    """What a read needs from an index row: provenance, the German hash it was made from and where the text is."""

    candidate_id: UUID
    locale: str
    source_hash: str
    source: TranslationSource
    engine: str
    storage_key: str
    content_sha256: str


_COLUMNS = (Row.candidate_id, Row.locale, Row.source_hash, Row.source, Row.engine, Row.storage_key, Row.content_sha256)


class TranslationIndexRepository(SessionRepository):
    """Read the translation index of one locale; the text itself is never in the database."""

    def translations_for(self, candidate_ids: Sequence[UUID], locale: str) -> dict[UUID, TranslationIndexRow]:
        """Return the index row of every id in ``candidate_ids`` that has a translation into exactly ``locale``.

        German is the source, never a translation target: it answers empty without a query.
        """
        if not candidate_ids or locale == DEFAULT_LOCALE:
            return {}
        stmt = select(*_COLUMNS).where(Row.candidate_id.in_(candidate_ids), Row.locale == locale)
        return {found.candidate_id: found for found in map(TranslationIndexRow._make, self._session.execute(stmt))}

    def translation_of(self, candidate_id: UUID, locale: str) -> TranslationIndexRow | None:
        """Return the index row of ``(candidate_id, locale)``, or ``None``; another locale is never substituted."""
        return self.translations_for([candidate_id], locale).get(candidate_id)
