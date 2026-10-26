"""Metadata row for an object-store artifact (snapshot or screenshot)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, Uuid
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.discovery.enums import DiscoveryArtifactKind, enum_values
from app.models.discovery.mixins import CreatedAtMixin


class DiscoveryArtifact(CreatedAtMixin, Base):
    """One stored file; the bytes live in the object store under ``storage_key``."""

    __tablename__ = "discovery_artifact"
    __table_args__ = (
        UniqueConstraint("catalogue_service_id", "kind", "sha256", name="uq_discovery_artifact_catalogue_kind_sha256"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    catalogue_service_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("catalogue_service.id", ondelete="CASCADE"), nullable=False, index=True
    )
    discovery_task_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("discovery_task.id", ondelete="SET NULL"), nullable=True
    )
    kind: Mapped[DiscoveryArtifactKind] = mapped_column(
        SAEnum(DiscoveryArtifactKind, name="discovery_artifact_kind", native_enum=True, values_callable=enum_values),
        nullable=False,
    )
    storage_key: Mapped[str] = mapped_column(String(300), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    final_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
