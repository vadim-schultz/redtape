from __future__ import annotations

import enum
from datetime import datetime
import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import Boolean, DateTime
from sqlalchemy import ForeignKey, String, UniqueConstraint, Uuid, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import func

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

    # OpenPLZ "type" (e.g. "Landkreis", "Kreisfreie Stadt", "Stadt", ...).
    # Keep it nullable so older rows from Wave 1 still work.
    openplz_type: Mapped[str | None] = mapped_column("type", String(128), nullable=True)

    # OpenPLZ municipality postalCode (primarily used for municipalities in Germany).
    postal_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    multiple_postal_codes: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )

    # Updated by the location import so Supabase/WAF caches can be refreshed.
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
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

    localities: Mapped[list["Locality"]] = relationship(
        "Locality",
        back_populates="municipality",
        foreign_keys="Locality.municipality_id",
    )
