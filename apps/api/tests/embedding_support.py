"""Builders shared by the embedding queue, completion and machine API tests."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from app.config import settings
from app.db import engine as db_engine
from app.models.api_key import ApiKey
from app.models.discovery import CatalogueService, DiscoveryDocumentCandidate
from app.models.jurisdiction import Jurisdiction
from app.models.search import EMBEDDING_DIM, CandidateSearchText, EmbeddingTask, WorkTaskStatus
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from search_support import make_candidate, open_tasks, search_service

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
"""The fixed instant the injected clocks return."""


def make_key(session: Session, name: str = "embed-drain") -> ApiKey:
    """Add an API key row and return it."""
    key = ApiKey(name=name, key_hash=uuid.uuid4().hex * 2, key_prefix=uuid.uuid4().hex[:8])
    session.add(key)
    session.flush()
    return key


def queued(session: Session, title: str = "Kindergeldantrag") -> tuple[DiscoveryDocumentCandidate, EmbeddingTask]:
    """Add a candidate, build its search text and return it with the pending task that text queued."""
    candidate = make_candidate(session, title)
    search_service(session).refresh(candidate.id)
    task = next(task for task in open_tasks(session) if task.candidate_id == candidate.id)
    return candidate, task


def claimed_by(session: Session, task: EmbeddingTask, key: ApiKey, *, attempts: int = 1) -> EmbeddingTask:
    """Put ``task`` in the state a claim by ``key`` leaves it in."""
    task.status = WorkTaskStatus.CLAIMED
    task.claimed_by_api_key_id = key.id
    task.claimed_at = NOW
    task.lease_expires_at = NOW + timedelta(minutes=15)
    task.attempt_count = attempts
    session.flush()
    return task


def current_hash(session: Session, task: EmbeddingTask) -> str:
    """Return the content hash of the search text ``task`` is for."""
    row = session.get(CandidateSearchText, (task.candidate_id, task.locale))
    assert row is not None
    return row.content_hash


def unit_vector(position: int = 0) -> list[float]:
    """Return a vector of the embedding width that is 1.0 at ``position`` and 0.0 elsewhere."""
    vector = [0.0] * EMBEDDING_DIM
    vector[position] = 1.0
    return vector


def task_states(session: Session) -> dict[uuid.UUID, WorkTaskStatus]:
    """Return the status of every embedding task by id."""
    return {task.id: task.status for task in session.scalars(select(EmbeddingTask))}


MODEL = settings.embedding_model


@dataclass(slots=True)
class CommittedWorld:
    """Rows committed for real so that separate connections see them; removed again by :func:`committed_world`."""

    candidate_ids: list[uuid.UUID] = field(default_factory=list)
    task_ids: list[uuid.UUID] = field(default_factory=list)
    key_ids: list[uuid.UUID] = field(default_factory=list)


def _forget(session: Session, world: CommittedWorld) -> None:
    """Delete everything the world committed, children first."""
    candidates = select(DiscoveryDocumentCandidate.jurisdiction_id).where(
        DiscoveryDocumentCandidate.id.in_(world.candidate_ids)
    )
    jurisdictions = list(session.scalars(candidates))
    session.execute(delete(DiscoveryDocumentCandidate).where(DiscoveryDocumentCandidate.id.in_(world.candidate_ids)))
    session.execute(delete(CatalogueService).where(CatalogueService.jurisdiction_id.in_(jurisdictions)))
    session.execute(delete(Jurisdiction).where(Jurisdiction.id.in_(jurisdictions)))
    session.execute(delete(ApiKey).where(ApiKey.id.in_(world.key_ids)))
    session.commit()


@contextmanager
def committed_world(tasks: int, keys: int = 2) -> Iterator[tuple[CommittedWorld, list[ApiKey]]]:
    """Commit ``tasks`` queued candidates and ``keys`` API keys on their own connection; delete them on exit."""
    world = CommittedWorld()
    with Session(bind=db_engine, expire_on_commit=False) as session:
        made = [queued(session, f"Committed Antrag {n}") for n in range(tasks)]
        api_keys = [make_key(session, f"committed-{n}") for n in range(keys)]
        world.candidate_ids = [candidate.id for candidate, _ in made]
        world.task_ids = [task.id for _, task in made]
        world.key_ids = [key.id for key in api_keys]
        session.commit()
        try:
            yield world, api_keys
        finally:
            session.rollback()
            _forget(session, world)
