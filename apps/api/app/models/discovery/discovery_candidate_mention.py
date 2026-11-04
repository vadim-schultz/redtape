"""One occurrence of a document candidate in a catalogue procedure."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, TypedDict

from sqlalchemy import ARRAY, Boolean, Float, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.discovery.enums import DiscoveryMentionRole, enum_values
from app.models.discovery.mixins import CreatedAtMixin

if TYPE_CHECKING:
    from app.models.discovery.catalogue_service import CatalogueService
    from app.models.discovery.discovery_document_candidate import DiscoveryDocumentCandidate


class PvogSourcePathData(TypedDict, total=False):
    """Typed PVOG path fields retained with a mention during the storage transition."""

    root_code: str
    root_label: str
    parent_code: str
    parent_label: str
    leaf_code: str
    leaf_label: str
    source_version: str


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
    artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("discovery_artifact.id", ondelete="SET NULL"), nullable=True
    )
    extractor: Mapped[str] = mapped_column(String(64), nullable=False)
    extractor_version: Mapped[str] = mapped_column(String(32), nullable=False)
    condition: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_optional: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    domain_codes: Mapped[list[str] | None] = mapped_column(ARRAY(String(64)), nullable=True)
    situation_codes: Mapped[list[str] | None] = mapped_column(ARRAY(String(64)), nullable=True)
    direct_domain_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    direct_situation_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    pvog_leaf_code: Mapped[str | None] = mapped_column(String(64), nullable=True)

    candidate: Mapped[DiscoveryDocumentCandidate] = relationship(
        "DiscoveryDocumentCandidate", back_populates="mentions"
    )
    catalogue_service: Mapped[CatalogueService] = relationship("CatalogueService")

    @property
    def category_codes(self) -> list[str] | None:
        """Return canonical categories during the compatibility storage window."""
        return self.domain_codes

    @category_codes.setter
    def category_codes(self, value: list[str] | None) -> None:
        """Store canonical categories in the legacy array until the storage cutover."""
        self.domain_codes = value

    @property
    def direct_category_confidence(self) -> float | None:
        """Return the strongest direct category confidence during the transition."""
        values = [
            value for value in (self.direct_domain_confidence, self.direct_situation_confidence) if value is not None
        ]
        return max(values, default=None)

    @direct_category_confidence.setter
    def direct_category_confidence(self, value: float | None) -> None:
        """Store canonical direct confidence in the legacy confidence slot."""
        self.direct_domain_confidence = value
        self.direct_situation_confidence = None

    @property
    def pvog_source_path(self) -> PvogSourcePathData | None:
        """Return captured PVOG path metadata carried through the current request."""
        return getattr(self, "_pvog_source_path", None)

    @pvog_source_path.setter
    def pvog_source_path(self, value: PvogSourcePathData | None) -> None:
        """Keep PVOG path metadata available to the current evidence pipeline."""
        self._pvog_source_path = value

    @property
    def pvog_mapping_version(self) -> str | None:
        """Return the frozen mapping version carried through the current request."""
        return getattr(self, "_pvog_mapping_version", None)

    @pvog_mapping_version.setter
    def pvog_mapping_version(self, value: str | None) -> None:
        """Keep the frozen mapping version available to the current evidence pipeline."""
        self._pvog_mapping_version = value
