"""Response models of the translation admin coverage route."""

from __future__ import annotations

from pydantic import BaseModel


class TranslationLocaleCoverage(BaseModel):
    """Card translation counts of one target locale.

    ``stale`` is a subset of ``translated``: a stored translation that an open task is replacing.
    ``pending`` counts the ready pending tasks, as the machine summary does.
    """

    locale: str
    translated: int
    stale: int
    pending: int
    claimed: int
    failed: int


class TranslationCoverageResponse(BaseModel):
    """Per target locale, how far the card units are translated, against the candidates that have a German card."""

    denominator: int
    locales: list[TranslationLocaleCoverage]
