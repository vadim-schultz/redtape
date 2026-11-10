"""Search schema (chapter 3): search text, embeddings and embedding tasks on the test database."""

from __future__ import annotations

import uuid

import pytest
from app.config import Settings
from app.models import ApiKey, Jurisdiction, JurisdictionKind
from app.models.discovery import DiscoveryDocumentCandidate
from app.models.search import (
    CANONICAL_LOCALE,
    EMBEDDING_DIM,
    CandidateEmbedding,
    CandidateSearchText,
    EmbeddingTask,
    WorkTaskStatus,
)
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError, StatementError
from sqlalchemy.orm import Session

MODEL = "@cf/qwen/qwen3-embedding-0.6b"
HASH = "a" * 64


def _candidate(session: Session) -> DiscoveryDocumentCandidate:
    country = Jurisdiction(kind=JurisdictionKind.COUNTRY, code=f"T{uuid.uuid4().hex[:8]}")
    session.add(country)
    session.flush()
    row = DiscoveryDocumentCandidate(jurisdiction_id=country.id, key=uuid.uuid4().hex, title_i18n={"de": "Antrag"})
    session.add(row)
    session.flush()
    return row


def _vec(*head: float) -> list[float]:
    """Return a full-width vector that starts with ``head`` and is zero elsewhere."""
    return [*head, *([0.0] * (EMBEDDING_DIM - len(head)))]


def _search_text(candidate: DiscoveryDocumentCandidate, body: str = "Kindergeld beantragen") -> CandidateSearchText:
    return CandidateSearchText(
        candidate_id=candidate.id,
        locale=CANONICAL_LOCALE,
        text=body,
        tsv_native=func.to_tsvector("german", body),
        tsv_simple=func.to_tsvector("simple", body),
        content_hash=HASH,
    )


def _embedding(candidate: DiscoveryDocumentCandidate, vector: list[float]) -> CandidateEmbedding:
    return CandidateEmbedding(
        candidate_id=candidate.id,
        model=MODEL,
        locale=CANONICAL_LOCALE,
        dim=EMBEDDING_DIM,
        text_hash=HASH,
        embedding=vector,
    )


def _task(candidate: DiscoveryDocumentCandidate, status: WorkTaskStatus = WorkTaskStatus.PENDING) -> EmbeddingTask:
    return EmbeddingTask(candidate_id=candidate.id, model=MODEL, locale=CANONICAL_LOCALE, text_hash=HASH, status=status)


def _count(session: Session, model: type[CandidateSearchText | CandidateEmbedding | EmbeddingTask]) -> int:
    return session.execute(select(func.count()).select_from(model)).scalar_one()


def test_search_text_stores_a_de_row_with_both_tsvectors_and_finds_it_by_tsquery(db_session: Session) -> None:
    """search text · stores a de row with both tsvectors and finds it by tsquery."""
    candidate = _candidate(db_session)
    db_session.add(_search_text(candidate))
    db_session.flush()

    native = select(CandidateSearchText.candidate_id).where(
        CandidateSearchText.tsv_native.op("@@")(func.websearch_to_tsquery("german", "Kindergelder"))
    )
    simple = select(CandidateSearchText.candidate_id).where(
        CandidateSearchText.tsv_simple.op("@@")(func.websearch_to_tsquery("simple", "kindergeld"))
    )

    assert db_session.execute(native).scalars().all() == [candidate.id]
    assert db_session.execute(simple).scalars().all() == [candidate.id]


def test_search_text_refuses_a_duplicate_candidate_and_locale(db_session: Session) -> None:
    """search text · duplicate (candidate, locale) is refused."""
    candidate = _candidate(db_session)
    db_session.add(_search_text(candidate))
    db_session.flush()

    db_session.add(_search_text(candidate, "Zweiter Text"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_embedding_stores_a_vector_and_orders_by_cosine_distance(db_session: Session) -> None:
    """embedding · stores a vector and orders by cosine distance, nearest first."""
    near, middle, far = (_candidate(db_session) for _ in range(3))
    db_session.add_all(
        [_embedding(near, _vec(1.0, 0.1)), _embedding(middle, _vec(1.0, 1.0)), _embedding(far, _vec(0.0, 1.0))]
    )
    db_session.flush()

    distance = CandidateEmbedding.embedding.cosine_distance(_vec(1.0, 0.0))
    nearest_first = db_session.execute(select(CandidateEmbedding.candidate_id).order_by(distance)).scalars().all()

    assert nearest_first == [near.id, middle.id, far.id]


def test_embedding_rejects_a_vector_of_the_wrong_dimension(db_session: Session) -> None:
    """embedding · rejects a vector of the wrong dimension instead of truncating it."""
    candidate = _candidate(db_session)
    db_session.add(_embedding(candidate, [1.0, 0.0, 0.0]))

    with pytest.raises((DBAPIError, StatementError)):
        db_session.flush()


def test_embedding_allows_one_row_per_candidate_model_and_locale(db_session: Session) -> None:
    """embedding · a second locale is a second row; the same model and locale twice is refused."""
    candidate = _candidate(db_session)
    db_session.add(_embedding(candidate, _vec(1.0)))
    other_locale = _embedding(candidate, _vec(1.0))
    other_locale.locale = "en"
    db_session.add(other_locale)
    db_session.flush()
    assert _count(db_session, CandidateEmbedding) == 2

    db_session.add(_embedding(candidate, _vec(0.5)))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_embedding_task_enqueues_one_pending_task_per_candidate_model_and_locale(db_session: Session) -> None:
    """embedding task · one pending task per (candidate, model, locale); a completed one does not block a new one."""
    candidate = _candidate(db_session)
    db_session.add(_task(candidate, WorkTaskStatus.COMPLETED))
    db_session.add(_task(candidate, WorkTaskStatus.FAILED))
    db_session.add(_task(candidate))
    db_session.flush()

    stored = db_session.execute(select(EmbeddingTask).where(EmbeddingTask.candidate_id == candidate.id)).scalars().all()

    assert sorted(task.status for task in stored) == sorted(
        [WorkTaskStatus.COMPLETED, WorkTaskStatus.FAILED, WorkTaskStatus.PENDING]
    )
    assert all(task.priority == 100 and task.attempt_count == 0 for task in stored)


@pytest.mark.parametrize("open_status", [WorkTaskStatus.PENDING, WorkTaskStatus.CLAIMED])
def test_embedding_task_refuses_a_second_open_task_for_the_same_candidate_and_model(
    db_session: Session, open_status: WorkTaskStatus
) -> None:
    """embedding task · a second open (pending or claimed) task for the same candidate and model is refused."""
    candidate = _candidate(db_session)
    db_session.add(_task(candidate, open_status))
    db_session.flush()

    db_session.add(_task(candidate))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_embedding_task_survives_deleting_the_claiming_api_key(db_session: Session) -> None:
    """embedding task · deleting the claiming API key keeps the task and clears the claimer."""
    key = ApiKey(name="embed", key_hash=uuid.uuid4().hex, key_prefix=uuid.uuid4().hex[:8])
    db_session.add(key)
    db_session.flush()
    task = _task(_candidate(db_session), WorkTaskStatus.CLAIMED)
    task.claimed_by_api_key_id = key.id
    db_session.add(task)
    db_session.flush()

    db_session.execute(delete(ApiKey).where(ApiKey.id == key.id))
    db_session.refresh(task)

    assert task.claimed_by_api_key_id is None
    assert task.status is WorkTaskStatus.CLAIMED


def test_candidate_delete_cascades_to_search_text_embeddings_and_tasks(db_session: Session) -> None:
    """candidate delete · cascades to search text, embeddings and tasks, and spares other candidates."""
    doomed, kept = _candidate(db_session), _candidate(db_session)
    for candidate in (doomed, kept):
        db_session.add_all([_search_text(candidate), _embedding(candidate, _vec(1.0)), _task(candidate)])
    db_session.flush()

    db_session.execute(delete(DiscoveryDocumentCandidate).where(DiscoveryDocumentCandidate.id == doomed.id))

    for model in (CandidateSearchText, CandidateEmbedding, EmbeddingTask):
        assert db_session.execute(select(model.candidate_id)).scalars().all() == [kept.id]


def test_model_dimension_matches_the_configured_embedding_dimension() -> None:
    """embedding · the column width equals the settings default, so a model change cannot drift silently."""
    assert CandidateEmbedding.embedding.type.dim == EMBEDDING_DIM == Settings(_env_file=None).embedding_dim


def test_vector_and_unaccent_extensions_are_installed(db_session: Session) -> None:
    """search schema · the extensions the tables and later queries rely on are present."""
    installed = db_session.execute(text("select extname from pg_extension where extname in ('vector', 'unaccent')"))
    assert sorted(installed.scalars().all()) == ["unaccent", "vector"]
