"""A staged ``parent requires required`` edge between two document candidates."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.discovery.enums import DiscoveryEdgeBasis, enum_values
from app.models.discovery.mixins import CreatedAtMixin


class DiscoveryCandidateEdge(CreatedAtMixin, Base):
    """One requirement between two candidates, with the procedure that states it as provenance."""

    __tablename__ = "discovery_candidate_edge"
    __table_args__ = (
        UniqueConstraint(
            "parent_candidate_id",
            "required_candidate_id",
            "catalogue_service_id",
            name="uq_discovery_candidate_edge_key",
        ),
        CheckConstraint("parent_candidate_id <> required_candidate_id", name="ck_discovery_candidate_edge_distinct"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_candidate_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("discovery_document_candidate.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    required_candidate_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("discovery_document_candidate.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    catalogue_service_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("catalogue_service.id", ondelete="CASCADE"), nullable=False, index=True
    )
    condition: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_optional: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    basis: Mapped[DiscoveryEdgeBasis] = mapped_column(
        SAEnum(DiscoveryEdgeBasis, name="discovery_edge_basis", native_enum=True, values_callable=enum_values),
        nullable=False,
    )
    extractor: Mapped[str] = mapped_column(String(64), nullable=False)
    extractor_version: Mapped[str] = mapped_column(String(32), nullable=False)
