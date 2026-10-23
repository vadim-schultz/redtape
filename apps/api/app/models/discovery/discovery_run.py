"""Operational run record: explicit worker-drain health."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.discovery.enums import DiscoveryRunKind, DiscoveryRunStatus


class DiscoveryRun(Base):
    """One bounded worker run, created at start and closed with its report."""

    __tablename__ = "discovery_run"
    __table_args__ = (Index("ix_discovery_run_status_finished_at", "status", "finished_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default=DiscoveryRunKind.WORKER_DRAIN.value)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=DiscoveryRunStatus.RUNNING.value, server_default=text("'running'")
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    claimed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    completed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    skipped_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    remaining_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stop_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
