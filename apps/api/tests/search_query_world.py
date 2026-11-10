"""Rows for the query-path tests: candidates with search texts per locale and embeddings of chosen similarity."""

from __future__ import annotations

import math
from dataclasses import replace

from app.config import Settings
from app.features.search.hashing import content_hash
from app.features.search.params import RetrievalParams
from app.features.search.query_embedder import QueryVector
from app.features.search.repository import SearchTextRepository
from app.features.search.text import BuiltText
from app.models.discovery import DiscoveryDocumentCandidate
from app.models.search import EMBEDDING_DIM, CandidateEmbedding
from sqlalchemy.orm import Session

from search_support import make_candidate, make_mention, search_service

MODEL = Settings(_env_file=None).embedding_model


def params(**overrides: object) -> RetrievalParams:
    """Return the retrieval parameters of the default settings with ``overrides`` applied."""
    return replace(RetrievalParams.from_settings(Settings(_env_file=None)), **overrides)  # type: ignore[arg-type]


def at_similarity(cosine: float) -> list[float]:
    """Return a vector whose cosine similarity to ``query_vector()`` is ``cosine``."""
    vector = [0.0] * EMBEDDING_DIM
    vector[0], vector[1] = cosine, math.sqrt(max(1.0 - cosine * cosine, 0.0))
    return vector


def query_vector() -> QueryVector:
    """Return the query vector all similarities are measured against (the first unit vector)."""
    return (1.0, *([0.0] * (EMBEDDING_DIM - 1)))


def add_text(session: Session, candidate: DiscoveryDocumentCandidate, locale: str, text: str) -> None:
    """Write the search text of ``candidate`` in ``locale`` with its tsvectors."""
    SearchTextRepository(session).upsert_search_text(candidate.id, BuiltText(locale, text, content_hash(text)))
    session.flush()


def add_embedding(
    session: Session,
    candidate: DiscoveryDocumentCandidate,
    vector: list[float],
    *,
    locale: str = "de",
    model: str = MODEL,
) -> None:
    """Store an embedding of ``candidate`` for ``locale`` and ``model``."""
    session.add(
        CandidateEmbedding(
            candidate_id=candidate.id, model=model, locale=locale, dim=EMBEDDING_DIM, text_hash="h", embedding=vector
        )
    )
    session.flush()


def indexed(
    session: Session,
    title: str,
    excerpt: str | None = None,
    *,
    similarity: float | None = None,
) -> DiscoveryDocumentCandidate:
    """Add a candidate with its German search text and, when ``similarity`` is given, a German embedding of it."""
    candidate = make_candidate(session, title)
    if excerpt:
        make_mention(session, candidate, excerpt)
    search_service(session).refresh(candidate.id)
    if similarity is not None:
        add_embedding(session, candidate, at_similarity(similarity))
    return candidate
