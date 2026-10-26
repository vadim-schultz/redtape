"""DTOs mirroring the discovery machine route for candidate mentions."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

MentionRole = Literal["required", "form"]
MAX_MENTION_ITEMS = 100


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


class MentionItem(MentionDraft):
    """A mention for ``POST /candidates/mentions``."""

    catalogue_service_id: UUID
    artifact_id: UUID | None = None


class MentionsRequest(BaseModel):
    """Batch of mentions recorded in one transaction."""

    items: list[MentionItem] = Field(min_length=1, max_length=MAX_MENTION_ITEMS)


class MentionsResponse(BaseModel):
    """What a mentions batch created or updated."""

    candidates_created: int
    mentions_created: int
    mentions_updated: int
