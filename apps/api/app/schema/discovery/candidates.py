"""Request and response models for the candidate mention machine route."""

from __future__ import annotations

from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models.discovery import DiscoveryMentionRole
from app.schema.locale.keys import LocaleKeyedMap
from app.shared.retired_taxonomy import RETIRED_TAXONOMY_FIELDS, retired_taxonomy_message

MAX_MENTION_ITEMS = 100
MAX_CONDITION_LENGTH = 300
MAX_CATEGORY_CODES = 5
Code = Annotated[str, Field(min_length=1, max_length=64)]


class PvogSourcePath(BaseModel):
    """Captured PVOG root, parent and leaf labels for one mention."""

    root_code: str | None = None
    root_label: str | None = None
    parent_code: str | None = None
    parent_label: str | None = None
    leaf_code: str | None = None
    leaf_label: str | None = None
    source_version: str | None = None


class CandidateMentionItem(BaseModel):
    """One occurrence of a document in a procedure."""

    model_config = {"extra": "forbid"}

    catalogue_service_id: UUID
    title_i18n: LocaleKeyedMap = Field(min_length=1)
    role: DiscoveryMentionRole
    excerpt: str = Field(min_length=1)
    source_field: str = Field(min_length=1, max_length=200)
    extractor: str = Field(min_length=1, max_length=64)
    extractor_version: str = Field(min_length=1, max_length=32)
    official_url: str | None = Field(default=None, min_length=1, max_length=500)
    artifact_id: UUID | None = None
    condition: str | None = Field(default=None, min_length=1, max_length=MAX_CONDITION_LENGTH)
    is_optional: bool | None = None
    category_codes: list[Code] | None = Field(default=None, max_length=MAX_CATEGORY_CODES)
    direct_category_confidence: float | None = Field(default=None, ge=0, le=1)
    pvog_leaf_code: Code | None = None
    pvog_source_path: PvogSourcePath | None = None
    pvog_mapping_version: Code | None = None

    @model_validator(mode="before")
    @classmethod
    def _reject_retired_fields(cls, value: object) -> object:
        """Reject retired axis fields with a validation error; a retired field is never silently translated."""
        if isinstance(value, dict):
            retired = sorted(RETIRED_TAXONOMY_FIELDS & value.keys())
            if retired:
                raise ValueError(retired_taxonomy_message(retired))
        return value

    @model_validator(mode="after")
    def _title_has_text(self) -> Self:
        if not any(value.strip() for value in self.title_i18n.values()):
            raise ValueError("title_i18n needs at least one non-blank value")
        return self


class CandidateMentionsRequest(BaseModel):
    """Batch of mentions recorded in one transaction."""

    items: list[CandidateMentionItem] = Field(min_length=1, max_length=MAX_MENTION_ITEMS)


class CandidateMentionsResponse(BaseModel):
    """What a mentions batch created or updated."""

    candidates_created: int
    mentions_created: int
    mentions_updated: int
    unknown_codes: int = 0
