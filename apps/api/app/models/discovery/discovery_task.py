"""Work queue row for fetch and enrich crawlers."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, Uuid, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.discovery.enums import DiscoveryTaskKind, DiscoveryTaskStatus, enum_values
from app.models.discovery.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.discovery.catalogue_service import CatalogueService
    from app.models.discovery.discovery_fetch_log import DiscoveryFetchLog


class DiscoveryTask(TimestampMixin, Base):
    """Queued unit of fetch or enrich work for the discovery pipeline."""

    __tablename__ = "discovery_task"
    __table_args__ = (Index("ix_discovery_task_status_priority_created_at", "status", "priority", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    catalogue_service_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("catalogue_service.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[DiscoveryTaskKind] = mapped_column(
        SAEnum(DiscoveryTaskKind, name="discovery_task_kind", native_enum=True, values_callable=enum_values),
        nullable=False,
    )
    target_url: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[DiscoveryTaskStatus] = mapped_column(
        SAEnum(DiscoveryTaskStatus, name="discovery_task_status", native_enum=True, values_callable=enum_values),
        nullable=False,
        default=DiscoveryTaskStatus.PENDING,
        server_default=text("'pending'"),
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100, server_default=text("100"))
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    claimed_by_api_key_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("api_key.id", ondelete="SET NULL"), nullable=True
    )
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    catalogue_service: Mapped[CatalogueService] = relationship("CatalogueService", back_populates="tasks")
    fetch_logs: Mapped[list[DiscoveryFetchLog]] = relationship(
        "DiscoveryFetchLog", back_populates="discovery_task", cascade="all, delete-orphan"
    )
