"""Resolvable discovery entity under a catalogue service."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.discovery.mixins import CreatedAtMixin

if TYPE_CHECKING:
    from app.models.discovery.catalogue_service import CatalogueService
    from app.models.discovery.discovery_claim import DiscoveryClaim


class DiscoveryEntity(CreatedAtMixin, Base):
    """URL or future document anchor tied to one catalogue row."""

    __tablename__ = "discovery_entity"
    __table_args__ = (UniqueConstraint("catalogue_service_id", "canonical_url", name="uq_discovery_entity_url"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    catalogue_service_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("catalogue_service.id", ondelete="CASCADE"), nullable=False, index=True
    )
    canonical_url: Mapped[str] = mapped_column(String(500), nullable=False)
    label: Mapped[str | None] = mapped_column(String(500), nullable=True)

    catalogue_service: Mapped[CatalogueService] = relationship(
        "CatalogueService", back_populates="entities", single_parent=True
    )
    claims: Mapped[list[DiscoveryClaim]] = relationship(
        "DiscoveryClaim", back_populates="discovery_entity", cascade="all, delete-orphan"
    )
