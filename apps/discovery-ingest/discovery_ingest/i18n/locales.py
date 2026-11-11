"""The locales the interface is translated into, and the English texts that may stay as they are in each."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

from pydantic import BaseModel, Field

from discovery_ingest.translation.locale_codes import DEFAULT_TARGET_LOCALES

UI_TARGET_LOCALES: Final = tuple(code for code in DEFAULT_TARGET_LOCALES if code != "en")
"""The five locales this command generates; the document locales minus ``en``, which has a hand-written file."""
UNCHANGED_FILE: Final = Path(__file__).parent / "data" / "unchanged.json"
EVERY_LOCALE: Final = "any"


class UnchangedFile(BaseModel):
    """English texts that are correct as they are: brand names and codes under ``any``, others per locale."""

    any: list[str] = Field(default_factory=list)
    tr: list[str] = Field(default_factory=list)
    ru: list[str] = Field(default_factory=list)
    uk: list[str] = Field(default_factory=list)
    pl: list[str] = Field(default_factory=list)
    ro: list[str] = Field(default_factory=list)


def allow_unchanged(locale: str) -> frozenset[str]:
    """Return the English texts that may come back unchanged in ``locale``."""
    data = UnchangedFile.model_validate(json.loads(UNCHANGED_FILE.read_text(encoding="utf-8")))
    return frozenset([*data.any, *getattr(data, locale, [])])
