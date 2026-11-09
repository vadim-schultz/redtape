"""DTOs mirroring the discovery machine route for candidate mentions."""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from discovery_ingest.pvog.models import PvogSourcePath

MentionRole = Literal["required", "form", "issued"]
MAX_MENTION_ITEMS = 100
MAX_CONDITION_LENGTH = 300
MAX_CATEGORY_CODES = 5
RETIRED_AXIS_FIELDS: frozenset[str] = frozenset(
    {"domain_codes", "situation_codes", "direct_domain_confidence", "direct_situation_confidence"}
)
Code = Annotated[str, Field(min_length=1, max_length=64)]


def refuse_retired_axis_fields(value: object) -> object:
    """Return ``value`` unchanged, or raise naming every retired domain or situation field it still carries."""
    if not isinstance(value, dict):
        return value
    retired = sorted(RETIRED_AXIS_FIELDS & value.keys())
    if retired:
        raise ValueError(f"retired field(s) {', '.join(retired)}; send category_codes instead")
    return value


class MentionDraft(BaseModel):
    """One document occurrence found in a source, before it is tied to a catalogue row."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    title_i18n: dict[str, str] = Field(min_length=1)
    role: MentionRole
    excerpt: str = Field(min_length=1)
    source_field: str = Field(min_length=1, max_length=200)
    extractor: str = Field(min_length=1, max_length=64)
    extractor_version: str = Field(min_length=1, max_length=32)
    official_url: str | None = Field(default=None, min_length=1, max_length=500)
    category_codes: list[Code] | None = Field(default=None, max_length=MAX_CATEGORY_CODES)
    direct_category_confidence: float | None = Field(default=None, ge=0, le=1)
    pvog_leaf_code: Code | None = Field(default=None)
    pvog_source_path: PvogSourcePath | None = None
    pvog_mapping_version: Code | None = None

    @model_validator(mode="before")
    @classmethod
    def _refuse_retired_axes(cls, value: object) -> object:
        """Refuse the retired domain and situation fields by name, before any category code is read."""
        return refuse_retired_axis_fields(value)


class MentionItem(MentionDraft):
    """A mention for ``POST /candidates/mentions``."""

    catalogue_service_id: UUID
    artifact_id: UUID | None = None
    condition: str | None = Field(default=None, min_length=1, max_length=MAX_CONDITION_LENGTH)
    is_optional: bool | None = None


class MentionsRequest(BaseModel):
    """Batch of mentions recorded in one transaction."""

    items: list[MentionItem] = Field(min_length=1, max_length=MAX_MENTION_ITEMS)


class MentionsResponse(BaseModel):
    """What a mentions batch created or updated."""

    candidates_created: int
    mentions_created: int
    mentions_updated: int
    unknown_codes: int = 0
