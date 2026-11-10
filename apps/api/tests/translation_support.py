"""Builders shared by the translation enqueue, queue, completion and machine API tests."""

from __future__ import annotations

from collections.abc import Sequence

from app.config import settings
from app.features.translation.enqueue import TranslationEnqueuer
from app.features.translation.source import SourceRepository
from app.features.translation.store import TranslationPayload, TranslationStore
from app.models.discovery import DiscoveryDocumentCandidate
from app.models.search import WorkTaskStatus
from app.models.translation import CandidateTranslation, TranslationSource, TranslationTask
from app.schema.translation.machine import TranslationCompleteItem
from app.shared.object_store import InMemoryObjectStore
from sqlalchemy import select
from sqlalchemy.orm import Session

from embedding_support import NOW, claimed_by, make_key
from search_support import make_candidate, make_mention

__all__ = [
    "LOCALES",
    "NOW",
    "claimed_by",
    "complete_item",
    "enqueuer",
    "human_row",
    "make_key",
    "queued_task",
    "stored_row",
    "task_rows",
    "unit_candidate",
    "unit_hash",
]

LOCALES = ("en", "tr")
"""The two target locales the enqueue tests use."""


def unit_candidate(
    session: Session,
    title: str = "Kindergeldantrag",
    excerpt: str = "Bitte Ausweis mitbringen",
    score: float | None = None,
) -> DiscoveryDocumentCandidate:
    """Add a candidate whose card unit is ``title`` and ``excerpt``; ``score`` is the confidence of its one category."""
    candidate = make_candidate(session, title)
    mention = make_mention(session, candidate, excerpt, score)
    if score is not None:
        mention.category_codes = ["home-and-housing"]
        session.flush()
    return candidate


def enqueuer(session: Session, locales: Sequence[str] = LOCALES) -> TranslationEnqueuer:
    """Return an enqueuer for ``locales``."""
    return TranslationEnqueuer(session, locales)


def unit_hash(session: Session, candidate: DiscoveryDocumentCandidate) -> str:
    """Return the current source hash of the candidate's card unit."""
    unit = SourceRepository(session).units_for([candidate.id])[candidate.id]
    return unit.source_hash


def task_rows(session: Session, status: WorkTaskStatus | None = None) -> list[TranslationTask]:
    """Return the translation tasks (of ``status`` when given), by priority, candidate and locale."""
    stmt = select(TranslationTask).order_by(
        TranslationTask.priority, TranslationTask.candidate_id, TranslationTask.locale
    )
    if status is not None:
        stmt = stmt.where(TranslationTask.status == status)
    return list(session.scalars(stmt))


def queued_task(
    session: Session, locale: str = "en", title: str = "Kindergeldantrag"
) -> tuple[DiscoveryDocumentCandidate, TranslationTask]:
    """Add a candidate, enqueue ``locale`` for it and return it with that pending task."""
    candidate = unit_candidate(session, title)
    enqueuer(session, (locale,)).enqueue_many([candidate.id])
    (task,) = [task for task in task_rows(session) if task.candidate_id == candidate.id]
    return candidate, task


def stored_row(
    session: Session, candidate: DiscoveryDocumentCandidate, locale: str, source_hash: str, key: str = "k/old.json"
) -> CandidateTranslation:
    """Add the index row of a machine translation of ``candidate`` at ``source_hash``."""
    row = CandidateTranslation(
        candidate_id=candidate.id,
        locale=locale,
        source_hash=source_hash,
        source=TranslationSource.MT,
        engine="llm",
        model="m",
        storage_key=key,
        content_sha256="c" * 64,
        size_bytes=10,
    )
    session.add(row)
    session.flush()
    return row


def human_row(session: Session, candidate: DiscoveryDocumentCandidate, locale: str) -> CandidateTranslation:
    """Add the index row of a human translation of ``candidate``."""
    row = stored_row(session, candidate, locale, unit_hash(session, candidate), key="k/human.json")
    row.source = TranslationSource.HUMAN
    session.flush()
    return row


def complete_item(task: TranslationTask, session: Session, **overrides: object) -> TranslationCompleteItem:
    """Return the item a worker posts for ``task`` at the current hash; ``overrides`` replace single fields."""
    fields: dict[str, object] = {
        "task_id": task.id,
        "source_hash": unit_hash(session, session.get(DiscoveryDocumentCandidate, task.candidate_id)),  # type: ignore[arg-type]
        "title": "Child benefit application",
        "description": "Please bring your ID",
        "engine": "llm",
        "model": "qwen",
    }
    return TranslationCompleteItem.model_validate({**fields, **overrides})


def written_payloads(backend: InMemoryObjectStore) -> list[TranslationPayload]:
    """Return every payload in ``backend``, in insertion order."""
    store = TranslationStore(backend)
    return [store.read(key) for key in backend.stored_keys()]


def configured_locales() -> tuple[str, ...]:
    """Return the locales the application settings translate into."""
    return settings.translation_target_locale_codes
