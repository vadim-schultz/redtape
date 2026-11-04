"""Pydantic models for the locales and translations API (read-only)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class LocaleRead(BaseModel):
    """One enabled locale and its translation completeness."""

    model_config = ConfigDict(from_attributes=True)

    code: str
    name_native: str
    name_english: str
    flag_emoji: str | None
    enabled: bool
    completeness_pct: float


class TranslationBundle(BaseModel):
    """Every UI translation string stored for one locale."""

    locale: str
    translations: dict[str, str]
