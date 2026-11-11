"""Read models of a stored translation: the availability summary on cards and the text behind the pop-over."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.models.translation import TranslationSource


class CandidateTranslationSummary(BaseModel):
    """That a stored translation exists for the request locale and who made it; never the text itself.

    ``stale`` is true when the German title or description changed after the translation was made.
    """

    model_config = ConfigDict(from_attributes=False)

    locale: str
    source: TranslationSource
    stale: bool


class CandidateTranslationText(BaseModel):
    """The stored translated title and description of one candidate, read from object storage."""

    model_config = ConfigDict(from_attributes=False)

    locale: str
    title: str
    description: str
    source: TranslationSource
    stale: bool
    engine: str
