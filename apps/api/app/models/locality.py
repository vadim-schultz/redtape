from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Uuid, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Locality(Base):
    """Postal-code locality row mapped to a municipality jurisdiction."""

    __tablename__ = "locality"

    __table_args__ = ()

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)

    municipality_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("jurisdiction.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    postal_code: Mapped[str] = mapped_column(String(16), nullable=False, index=True)

    # Native OpenPLZ name (German) used as a stable identifier for uniqueness.
    name: Mapped[str] = mapped_column(String(256), nullable=False)

    name_i18n: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    municipality = relationship(
        "Jurisdiction",
        back_populates="localities",
        foreign_keys=[municipality_id],
    )
