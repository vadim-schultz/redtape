"""The Azure probe's units: the reviewed sample of German card units, and the synthetic units of the token cases.

The sample is exported by the operator from production, reviewed and committed; the repository holds no copy of it, and
the probe refuses to run without it. The synthetic units are probe code, not production text: each carries a placeholder,
a plural count or a URL, which is what the probe measures.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

from pydantic import BaseModel, Field, TypeAdapter

from discovery_ingest.translation.units import TranslationUnit

FIXTURE_PATH: Final = Path("tests/fixtures/azure_probe_units.json")
"""The default sample, read relative to the working directory: run the probe from apps/discovery-ingest, or pass ``--units``."""

TOKEN_UNITS: Final = (
    TranslationUnit("probe.token.1", "Unterlagen von {name} prüfen: https://example.test/unterlagen", ""),
    TranslationUnit("probe.token.2", "{name} erhält die Nachricht bis 01.03.2025", ""),
)
"""Named placeholders and a URL: the machine path protects each placeholder as a token ⟦n⟧ and restores it after the call."""
PLURAL_UNITS: Final = (
    TranslationUnit("probe.count_one", "{count} Datei hochgeladen", ""),
    TranslationUnit("probe.count_other", "{count} Dateien hochgeladen", ""),
)
"""Plural forms: a CLDR sample number stands in for ``{count}`` during the call and comes back after it."""


class ProbeFixtureError(ValueError):
    """The sample is missing, empty or not a list of units; the message names the file."""


class _FixtureUnit(BaseModel):
    key: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = ""


_UNITS: Final = TypeAdapter(list[_FixtureUnit])


def load_units(path: Path = FIXTURE_PATH) -> tuple[TranslationUnit, ...]:
    """Return the units of the sample at ``path`` (a JSON list of key, title and description).

    Raises :class:`ProbeFixtureError` naming ``path`` when the file is missing, empty or malformed.
    """
    if not path.is_file():
        raise ProbeFixtureError(f"{path} is missing: put the reviewed sample of German card units there")
    try:
        items = _UNITS.validate_python(json.loads(path.read_text(encoding="utf-8")))
    except ValueError as err:
        raise ProbeFixtureError(f"{path} is not a JSON list of units with key, title and description") from err
    if not items:
        raise ProbeFixtureError(f"{path} is empty: the probe needs the reviewed sample of German card units")
    return tuple(TranslationUnit(item.key, item.title, item.description) for item in items)
