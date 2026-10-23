"""One occurrence of a document candidate in a catalogue procedure."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.discovery.enums import DiscoveryMentionRole, enum_values
from app.models.discovery.mixins import CreatedAtMixin

if TYPE_CHECKING:
    from app.models.discovery.catalogue_service import CatalogueService
    from app.models.discovery.discovery_document_candidate import DiscoveryDocumentCandidate


class DiscoveryCandidateMention(CreatedAtMixin, Base):
    """Provenance and ``requires`` relation of a candidate within one procedure."""

    __tablename__ = "discovery_candidate_mention"
    __table_args__ = (
        UniqueConstraint(
            "candidate_id",
            "catalogue_service_id",
            "role",
            "source_field",
            name="uq_discovery_candidate_mention_key",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("discovery_document_candidate.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    catalogue_service_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("catalogue_service.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[DiscoveryMentionRole] = mapped_column(
        SAEnum(DiscoveryMentionRole, name="discovery_mention_role", native_enum=True, values_callable=enum_values),
        nullable=False,
    )
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    source_field: Mapped[str] = mapped_column(String(200), nullable=False)
    artifact_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    extractor: Mapped[str] = mapped_column(String(64), nullable=False)
    extractor_version: Mapped[str] = mapped_column(String(32), nullable=False)

    candidate: Mapped[DiscoveryDocumentCandidate] = relationship(
        "DiscoveryDocumentCandidate", back_populates="mentions"
    )
    catalogue_service: Mapped[CatalogueService] = relationship("CatalogueService")
