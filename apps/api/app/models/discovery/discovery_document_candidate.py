"""Deduplicated document candidate harvested from catalogue procedures."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, UniqueConstraint, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.discovery.enums import DiscoveryCandidateStatus, enum_values
from app.models.discovery.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.discovery.discovery_candidate_mention import DiscoveryCandidateMention


class DiscoveryDocumentCandidate(TimestampMixin, Base):
    """One not yet emitted document name, unique per jurisdiction and promotion slug."""

    __tablename__ = "discovery_document_candidate"
    __table_args__ = (UniqueConstraint("jurisdiction_id", "key", name="uq_discovery_candidate_jurisdiction_key"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    jurisdiction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("jurisdiction.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(String(200), nullable=False)
    title_i18n: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    official_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[DiscoveryCandidateStatus] = mapped_column(
        SAEnum(
            DiscoveryCandidateStatus,
            name="discovery_candidate_status",
            native_enum=True,
            values_callable=enum_values,
        ),
        nullable=False,
        default=DiscoveryCandidateStatus.STAGED,
        server_default=text("'staged'"),
    )
    suggestion_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)

    mentions: Mapped[list[DiscoveryCandidateMention]] = relationship(
        "DiscoveryCandidateMention", back_populates="candidate", passive_deletes=True
    )
