"""DTOs mirroring the discovery machine route for candidate mentions."""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

MentionRole = Literal["required", "form", "issued"]
MAX_MENTION_ITEMS = 100
MAX_CONDITION_LENGTH = 300
MAX_DOMAIN_CODES = 2
MAX_SITUATION_CODES = 3
Code = Annotated[str, Field(min_length=1, max_length=64)]


class MentionDraft(BaseModel):
    """One document occurrence found in a source, before it is tied to a catalogue row."""

    model_config = ConfigDict(frozen=True)

    title_i18n: dict[str, str] = Field(min_length=1)
    role: MentionRole
    excerpt: str = Field(min_length=1)
    source_field: str = Field(min_length=1, max_length=200)
    extractor: str = Field(min_length=1, max_length=64)
    extractor_version: str = Field(min_length=1, max_length=32)
    official_url: str | None = Field(default=None, min_length=1, max_length=500)
    domain_codes: list[Code] | None = Field(default=None, max_length=MAX_DOMAIN_CODES)
    situation_codes: list[Code] | None = Field(default=None, max_length=MAX_SITUATION_CODES)


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
