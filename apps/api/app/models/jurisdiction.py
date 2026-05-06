from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, UniqueConstraint, Uuid, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class JurisdictionKind(str, enum.Enum):
    """Primary classification of a jurisdiction row."""

    COUNTRY = "COUNTRY"
    REGION = "REGION"
    MUNICIPALITY = "MUNICIPALITY"


class Jurisdiction(Base):
    """Unified administrative unit: geographic parent + one or more administrative roles."""

    __tablename__ = "jurisdiction"
    __table_args__ = (
        UniqueConstraint(
            "geographic_parent_id",
            "code",
            name="uq_jurisdiction_parent_code",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    kind: Mapped[JurisdictionKind] = mapped_column(
        SAEnum(JurisdictionKind, name="jurisdiction_kind", native_enum=True),
        nullable=False,
    )
    geographic_parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("jurisdiction.id", ondelete="RESTRICT"),
        nullable=True,
    )
    code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    administrative_roles: Mapped[list[str]] = mapped_column(
        ARRAY(String(64)),
        nullable=False,
        server_default=text("'{}'::character varying[]"),
    )
    name_i18n: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    geographic_parent: Mapped[Jurisdiction | None] = relationship(
        "Jurisdiction",
        remote_side=[id],
        foreign_keys=[geographic_parent_id],
        back_populates="geographic_children",
    )
    geographic_children: Mapped[list[Jurisdiction]] = relationship(
        "Jurisdiction",
        foreign_keys=[geographic_parent_id],
        back_populates="geographic_parent",
    )
