"""DTOs mirroring the discovery machine route for candidate mentions."""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from discovery_ingest.pvog.crosswalk_lookup import LegacyContext, crosswalk_from
from discovery_ingest.pvog.models import PvogSourcePath

MentionRole = Literal["required", "form", "issued"]
MAX_MENTION_ITEMS = 100
MAX_CONDITION_LENGTH = 300
MAX_CATEGORY_CODES = 5
# Compatibility bounds retained for old readers while workers drain.
MAX_DOMAIN_CODES = 2
MAX_SITUATION_CODES = 3
Code = Annotated[str, Field(min_length=1, max_length=64)]


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
    def _translate_legacy_axes(cls, value: object, info: LegacyContext) -> object:
        """Translate old axis fields once while old workers drain, through the crosswalk given as context."""
        if not isinstance(value, dict):
            return value
        legacy_fields = {"domain_codes", "situation_codes", "direct_domain_confidence", "direct_situation_confidence"}
        if not legacy_fields & value.keys():
            return value
        if "category_codes" in value:
            raise ValueError("legacy domain/situation fields cannot be combined with category_codes")
        crosswalk = crosswalk_from(info)
        domains = tuple(value.get("domain_codes") or ())
        situations = tuple(value.get("situation_codes") or ())
        categories = crosswalk.legacy_categories("domain", domains) + crosswalk.legacy_categories(
            "life_situation", situations
        )
        direct = max(
            (
                confidence
                for confidence in (
                    value.get("direct_domain_confidence"),
                    value.get("direct_situation_confidence"),
                )
                if confidence is not None
            ),
            default=None,
        )
        translated = {key: item for key, item in value.items() if key not in legacy_fields}
        translated["category_codes"] = list(dict.fromkeys(categories)) or None
        if direct is not None:
            translated["direct_category_confidence"] = direct
        return translated


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
