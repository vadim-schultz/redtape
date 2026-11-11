"""Session settings of a vector search: iterative HNSW scans so filters do not starve the leg, or an exact scan."""

from __future__ import annotations

import logging
from typing import Final

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

MIN_ITERATIVE_VERSION: Final = (0, 8)
"""The first pgvector release with iterative index scans. An older one ignores the setting silently."""
EXACT_SCAN: Final = text("SET LOCAL enable_indexscan = off")
"""Without plain index scans the planner reads the table and sorts, which is exact and takes milliseconds here."""
_VERSION: Final = text("select extversion from pg_extension where extname = 'vector'")


def apply_vector_scan(session: Session, *, index_enabled: bool) -> None:
    """Set, for the current transaction, how the vector leg scans.

    With the index on, ``hnsw.iterative_scan = relaxed_order`` keeps scanning until enough rows pass the filters. An
    older pgvector would accept the setting and ignore it, so the version is checked and the exact scan is used
    instead. With the index off the exact scan is forced, which is the diagnostic switch.
    """
    if index_enabled and _supports_iterative_scan(session):
        session.execute(select(func.set_config("hnsw.iterative_scan", "relaxed_order", True)))
        return
    session.execute(EXACT_SCAN)


def _supports_iterative_scan(session: Session) -> bool:
    """Whether the installed pgvector is 0.8 or later."""
    version = session.execute(_VERSION).scalar()
    parts = tuple(int(part) for part in str(version).split(".")[:2] if part.isdigit())
    if parts >= MIN_ITERATIVE_VERSION:
        return True
    logger.warning("pgvector %s has no iterative HNSW scan; the vector leg uses an exact scan", version)
    return False
