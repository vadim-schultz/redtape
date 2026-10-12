"""Append-only lineage events for the discovery pipeline."""

from __future__ import annotations

import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Index, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.discovery.enums import DiscoveryEventType, enum_values
from app.models.discovery.mixins import CreatedAtMixin


class DiscoveryEvent(CreatedAtMixin, Base):
    """Immutable audit row for catalogue, task, and emit activity."""

    __tablename__ = "discovery_event"
    __table_args__ = (Index("ix_discovery_event_catalogue_created_at", "catalogue_service_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type: Mapped[DiscoveryEventType] = mapped_column(
        SAEnum(DiscoveryEventType, name="discovery_event_type", native_enum=True, values_callable=enum_values),
        nullable=False,
    )
    catalogue_service_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("catalogue_service.id", ondelete="SET NULL"), nullable=True
    )
    discovery_task_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("discovery_task.id", ondelete="SET NULL"), nullable=True
    )
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
