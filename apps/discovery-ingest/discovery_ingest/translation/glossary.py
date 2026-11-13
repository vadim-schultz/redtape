"""The per-locale glossary: fixed renderings of domain terms and a do-not-translate list, both read from data files.

An adapter applies the glossary in the way its provider supports (prompt text for an LLM); the validators check
adherence whichever way it was applied. Add a term by editing ``glossary_data/<locale>.json``, not code.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Final, Literal

from pydantic import BaseModel, Field

DATA_DIR: Final = Path(__file__).parent / "glossary_data"
COMMON_FILE: Final = "_common"
GlossaryMode = Literal["strict", "advisory"]
"""``strict``: a glossary finding fails the unit. ``advisory``: it is recorded and the unit passes (TRANSLATION_GLOSSARY_MODE)."""
DEFAULT_GLOSSARY_MODE: Final[GlossaryMode] = "strict"


@dataclass(frozen=True, slots=True)
class GlossaryEntry:
    """A German term and the rendering the target language must use for it."""

    source: str
    rendering: str


@dataclass(frozen=True, slots=True)
class Glossary:
    """Terms with a fixed rendering, and terms (proper nouns, agencies, law abbreviations) that stay as written.

    ``mode`` says whether a finding of adherence fails the unit (strict) or is only recorded (advisory).
    """

    terms: tuple[GlossaryEntry, ...] = ()
    keep: tuple[str, ...] = ()
    mode: GlossaryMode = DEFAULT_GLOSSARY_MODE


class UnknownGlossaryError(LookupError):
    """There is no glossary data file for the locale."""


class GlossaryFile(BaseModel):
    """The shape of one data file: ``terms`` maps a German term to its rendering, ``keep`` lists unchanged terms."""

    terms: dict[str, str] = Field(default_factory=dict)
    keep: list[str] = Field(default_factory=list)


def _read(name: str) -> GlossaryFile:
    path = DATA_DIR / f"{name}.json"
    if not path.is_file():
        raise UnknownGlossaryError(f"no glossary data file for {name!r}")
    return GlossaryFile.model_validate(json.loads(path.read_text(encoding="utf-8")))


@lru_cache(maxsize=32)
def load_glossary(locale: str, mode: GlossaryMode = DEFAULT_GLOSSARY_MODE) -> Glossary:
    """Return the glossary of ``locale`` at ``mode``: its own terms and the shared plus its own do-not-translate list."""
    own, common = _read(locale), _read(COMMON_FILE)
    terms = tuple(GlossaryEntry(source, rendering) for source, rendering in own.terms.items())
    return Glossary(terms=terms, keep=tuple(dict.fromkeys([*common.keep, *own.keep])), mode=mode)
