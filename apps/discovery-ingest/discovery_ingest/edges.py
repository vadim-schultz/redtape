"""DTOs mirroring the discovery machine route for staged requirement edges."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from discovery_ingest.mentions import MAX_CONDITION_LENGTH

EdgeBasis = Literal["explicit", "derived_single_issued"]


class EdgeItem(BaseModel):
    """One ``parent requires required`` edge for ``POST /candidates/edges``; both endpoints must already be candidates."""

    model_config = ConfigDict(frozen=True)

    catalogue_service_id: UUID
    parent_title_i18n: dict[str, str] = Field(min_length=1)
    required_title_i18n: dict[str, str] = Field(min_length=1)
    basis: EdgeBasis
    condition: str | None = Field(default=None, min_length=1, max_length=MAX_CONDITION_LENGTH)
    is_optional: bool | None = None
    excerpt: str = Field(min_length=1)
    extractor: str = Field(min_length=1, max_length=64)
    extractor_version: str = Field(min_length=1, max_length=32)
