"""ORM model for fair task selection state tracking.

Tracks the phase of each entity (candidate or catalogue_service) in each pipeline,
enabling breadth-first coverage before depth-first completion.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class FairSelectionState(Base):
    """Tracks phase and coverage state for fair task selection across pipelines.

    One row per (pipeline, entity_id) pair. The entity_id refers to either a
    candidate_id (for translation/embedding) or a catalogue_service_id (for
    snapshot_translation/discovery). Phase starts at 1 and transitions through
    phases based on coverage progress.
    """

    __tablename__ = "fair_selection_state"
    __table_args__ = (
        Index(
            "ix_fair_selection_state_pipeline_entity",
            "pipeline",
            "entity_id",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pipeline: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    phase: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))
    coverage_bitmap: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default=text("0"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
