"""Staging claim before emit to the suggestion API."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Numeric, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.discovery.enums import DiscoveryClaimKind, enum_values
from app.models.discovery.mixins import CreatedAtMixin

if TYPE_CHECKING:
    from app.models.discovery.discovery_entity import DiscoveryEntity


class DiscoveryClaim(CreatedAtMixin, Base):
    """Proposed document or requirement edge extracted from a discovery entity."""

    __tablename__ = "discovery_claim"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    discovery_entity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("discovery_entity.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[DiscoveryClaimKind] = mapped_column(
        SAEnum(DiscoveryClaimKind, name="discovery_claim_kind", native_enum=True, values_callable=enum_values),
        nullable=False,
    )
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)

    discovery_entity: Mapped[DiscoveryEntity] = relationship("DiscoveryEntity", back_populates="claims")
