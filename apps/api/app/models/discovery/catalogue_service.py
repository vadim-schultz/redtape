"""Staging catalogue row for an imported Leistung / OZG service."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint, Uuid, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.discovery.enums import DiscoverySource, enum_values
from app.models.discovery.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.discovery.discovery_entity import DiscoveryEntity
    from app.models.discovery.discovery_task import DiscoveryTask

CK_PIPELINE_STAGE = "ck_catalogue_service_pipeline_stage"
UQ_SOURCE_EXTERNAL_ID = "uq_catalogue_service_source_external_id"


class CatalogueService(TimestampMixin, Base):
    """Imported service metadata in the discovery staging graph."""

    __tablename__ = "catalogue_service"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name=UQ_SOURCE_EXTERNAL_ID),
        CheckConstraint(
            "pipeline_stage IN ('T0', 'T1', 'T2', 'T3', 'T4')",
            name=CK_PIPELINE_STAGE,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[DiscoverySource] = mapped_column(
        SAEnum(DiscoverySource, name="discovery_source", native_enum=True, values_callable=enum_values),
        nullable=False,
    )
    external_id: Mapped[str] = mapped_column(String(200), nullable=False)
    jurisdiction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("jurisdiction.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    title_i18n: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    description_i18n: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    portal_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    pipeline_stage: Mapped[str] = mapped_column(String(2), nullable=False)

    entities: Mapped[list[DiscoveryEntity]] = relationship(
        "DiscoveryEntity",
        back_populates="catalogue_service",
        cascade="all, delete-orphan",
    )
    tasks: Mapped[list[DiscoveryTask]] = relationship(
        "DiscoveryTask",
        back_populates="catalogue_service",
        cascade="all, delete-orphan",
    )
