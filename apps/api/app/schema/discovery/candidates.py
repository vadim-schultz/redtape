"""Request and response models for the candidate mention machine route."""

from __future__ import annotations

from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.features.suggestions.slugs import pick_title
from app.models.discovery import DiscoveryMentionRole

MAX_MENTION_ITEMS = 100
MAX_CONDITION_LENGTH = 300
MAX_DOMAIN_CODES = 2
MAX_SITUATION_CODES = 3
Code = Annotated[str, Field(min_length=1, max_length=64)]


class CandidateMentionItem(BaseModel):
    """One occurrence of a document in a procedure."""

    catalogue_service_id: UUID
    title_i18n: dict[str, str] = Field(min_length=1)
    role: DiscoveryMentionRole
    excerpt: str = Field(min_length=1)
    source_field: str = Field(min_length=1, max_length=200)
    extractor: str = Field(min_length=1, max_length=64)
    extractor_version: str = Field(min_length=1, max_length=32)
    official_url: str | None = Field(default=None, min_length=1, max_length=500)
    artifact_id: UUID | None = None
    condition: str | None = Field(default=None, min_length=1, max_length=MAX_CONDITION_LENGTH)
    is_optional: bool | None = None
    domain_codes: list[Code] | None = Field(default=None, max_length=MAX_DOMAIN_CODES)
    situation_codes: list[Code] | None = Field(default=None, max_length=MAX_SITUATION_CODES)
    direct_domain_confidence: float | None = None
    direct_situation_confidence: float | None = None
    pvog_leaf_code: Code | None = None

    @model_validator(mode="after")
    def _title_has_text(self) -> Self:
        if not pick_title(self.title_i18n):
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
