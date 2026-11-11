"""Builders shared by the per-locale search-text tests: translation payloads, stored objects and keyword hits."""

from __future__ import annotations

import uuid

from app.features.search.keyword import keyword_leg
from app.features.search.query import NormalisedQuery
from app.features.translation.repository import TranslationRepository
from app.features.translation.store import StoredObject, TranslationPayload, TranslationStore
from app.models.discovery import DiscoveryDocumentCandidate
from app.models.search import CandidateSearchText, EmbeddingTask
from app.models.translation import CandidateTranslation, TranslationSource
from app.shared.object_store import InMemoryObjectStore
from sqlalchemy import select
from sqlalchemy.orm import Session

from search_query_world import params
from translation_support import unit_hash

TURKISH_TITLE = "Çocuk parası başvurusu"
TURKISH_DESCRIPTION = "Kimlikler ve evrak getirin"


def payload(
    locale: str = "tr",
    title: str = TURKISH_TITLE,
    description: str = TURKISH_DESCRIPTION,
    *,
    source: TranslationSource = TranslationSource.MT,
) -> TranslationPayload:
    """Return the payload of a translation of a card into ``locale``."""
    return TranslationPayload(
        locale=locale,
        title=title,
        description=description,
        source_hash="h" * 64,
        source=source,
        engine="llm",
        model="qwen",
    )


def store_translation(
    session: Session,
    backend: InMemoryObjectStore,
    candidate: DiscoveryDocumentCandidate,
    translated: TranslationPayload,
) -> StoredObject:
    """Write ``translated`` to ``backend`` and add its index row, as chapter 14's completion does."""
    stored = TranslationStore(backend).write(candidate.id, translated)
    current = translated.model_copy(update={"source_hash": unit_hash(session, candidate)})
    TranslationRepository(session).upsert_row(candidate.id, current, stored, None)
    return stored


def keyword_hits(session: Session, text: str, locale: str) -> list[uuid.UUID]:
    """Return the candidate ids the keyword leg finds for ``text`` read in ``locale``, best first."""
    leg = keyword_leg(NormalisedQuery(text, locale), params(), None)
    return [row.candidate_id for row in session.execute(leg.order_by("rnk")).all()]


def search_text_row(session: Session, candidate: DiscoveryDocumentCandidate, locale: str) -> CandidateSearchText | None:
    """Return the search-text row of ``candidate`` in ``locale``, or ``None``."""
    stmt = select(CandidateSearchText).where(
        CandidateSearchText.candidate_id == candidate.id, CandidateSearchText.locale == locale
    )
    return session.scalars(stmt).first()


def embedding_tasks(session: Session, locale: str | None = None) -> list[EmbeddingTask]:
    """Return the embedding tasks (of ``locale`` when given), oldest first."""
    stmt = select(EmbeddingTask).order_by(EmbeddingTask.created_at, EmbeddingTask.id)
    if locale is not None:
        stmt = stmt.where(EmbeddingTask.locale == locale)
    return list(session.scalars(stmt))


def indexed_row(session: Session, candidate: DiscoveryDocumentCandidate) -> CandidateTranslation | None:
    """Return the index row of any translation of ``candidate``, or ``None``."""
    stmt = select(CandidateTranslation).where(CandidateTranslation.candidate_id == candidate.id)
    return session.scalars(stmt).first()
