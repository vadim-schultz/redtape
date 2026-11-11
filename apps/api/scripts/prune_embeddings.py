"""Delete one locale's embeddings and open embedding tasks, and print the vector bytes reclaimed.

Run it to give up a locale whose vectors do not earn their space (rollout invariant 11). Remove the locale from
``EMBEDDING_LOCALES`` first, or the next stored translation queues it again. Search text and
full-text vectors stay, so the locale remains keyword-searchable. To embed the locale again, add it to
``EMBEDDING_LOCALES`` and run ``scripts.backfill_search --locale <code>``. The figure counts the stored vector
bytes; the table and its HNSW index only return the space to the operating system after a vacuum.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass

from app.db import SessionLocal
from app.models.search import CandidateEmbedding, EmbeddingTask, WorkTaskStatus
from app.shared.locale import SUPPORTED_LOCALES
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

_OPEN = (WorkTaskStatus.PENDING, WorkTaskStatus.CLAIMED)


@dataclass(frozen=True, slots=True)
class PruneReport:
    """What a prune removed for one locale."""

    locale: str
    vectors: int
    tasks: int
    bytes_reclaimed: int


def _vector_totals(session: Session, locale: str) -> tuple[int, int]:
    """Return how many vectors ``locale`` has and the bytes they occupy."""
    size = func.coalesce(func.sum(func.pg_column_size(CandidateEmbedding.embedding)), 0)
    count, total = session.execute(select(func.count(), size).where(CandidateEmbedding.locale == locale)).one()
    return count, int(total)


def _delete_open_tasks(session: Session, locale: str) -> int:
    """Delete the pending and claimed tasks of ``locale`` and return how many there were."""
    stmt = delete(EmbeddingTask).where(EmbeddingTask.locale == locale, EmbeddingTask.status.in_(_OPEN))
    return len(session.execute(stmt.returning(EmbeddingTask.id)).all())


def run_prune(session: Session, locale: str) -> PruneReport:
    """Delete the embeddings and open tasks of ``locale`` and commit; other locales are never touched."""
    vectors, bytes_reclaimed = _vector_totals(session, locale)
    session.execute(delete(CandidateEmbedding).where(CandidateEmbedding.locale == locale))
    tasks = _delete_open_tasks(session, locale)
    session.commit()
    return PruneReport(locale, vectors, tasks, bytes_reclaimed)


def format_report(report: PruneReport) -> str:
    """Return the prune as text: what was deleted and the vector bytes reclaimed."""
    return (
        f"locale={report.locale}: deleted {report.vectors} vectors and {report.tasks} open tasks; "
        f"reclaimed {report.bytes_reclaimed} vector bytes (run VACUUM to return the table and index space)"
    )


def _parse_options(argv: Sequence[str] | None) -> str:
    parser = argparse.ArgumentParser(description="Delete one locale's embeddings and open embedding tasks.")
    parser.add_argument("--locale", required=True, choices=sorted(spec.code for spec in SUPPORTED_LOCALES))
    return str(parser.parse_args(argv).locale)


def main(argv: Sequence[str] | None = None) -> int:
    """Prune the locale given on the command line from the configured database and print the report."""
    locale = _parse_options(argv)
    with SessionLocal() as session:
        print(format_report(run_prune(session, locale)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
