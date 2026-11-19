"""Append-only HTTP fetch attempt log."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.discovery.discovery_task import DiscoveryTask


class DiscoveryFetchLog(Base):
    """One fetch attempt against a discovery task target."""

    __tablename__ = "discovery_fetch_log"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    discovery_task_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("discovery_task.id", ondelete="CASCADE"), nullable=False, index=True
    )
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    content_type: Mapped[str | None] = mapped_column(String(200), nullable=True)
    byte_length: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)

    discovery_task: Mapped[DiscoveryTask] = relationship("DiscoveryTask", back_populates="fetch_logs")
