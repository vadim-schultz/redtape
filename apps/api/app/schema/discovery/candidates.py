"""Request and response models for the candidate mention machine route."""

from __future__ import annotations

from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models.discovery import DiscoveryMentionRole

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
    category_codes: list[Code] | None = Field(default=None, max_length=MAX_CATEGORY_CODES)
    direct_category_confidence: float | None = Field(default=None, ge=0, le=1)
    pvog_leaf_code: Code | None = None
    pvog_source_path: PvogSourcePath | None = None
    pvog_mapping_version: Code | None = None

    @model_validator(mode="before")
    @classmethod
    def _translate_legacy_axes(cls, value: object) -> object:
        """Translate old axis fields at the request boundary while old workers drain."""
        if not isinstance(value, dict):
            return value
        legacy_fields = {"domain_codes", "situation_codes", "direct_domain_confidence", "direct_situation_confidence"}
        if not legacy_fields & value.keys():
            return value
        if "category_codes" in value:
            raise ValueError("legacy domain/situation fields cannot be combined with category_codes")
        from app.shared.taxonomy_compatibility import LegacyTaxonomyAdapter

        try:
            translated = LegacyTaxonomyAdapter().translate(
                domain_codes=tuple(value.get("domain_codes") or ()),
                group_codes=(),
                situation_codes=tuple(value.get("situation_codes") or ()),
            )
        except ValueError as exc:
            raise ValueError(f"legacy taxonomy input is invalid: {exc}") from exc
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
        translated_value = {key: item for key, item in value.items() if key not in legacy_fields}
        translated_value["category_codes"] = (
            list(dict.fromkeys((*translated.domain_targets, *translated.situation_targets))) or None
        )
        if direct is not None:
            translated_value["direct_category_confidence"] = direct
        return translated_value

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
