"""The review manifest (``review.json``): per locale whether its strings are machine text or have been reviewed.

A locale stays ``machine`` until a native speaker's review is recorded by hand; only then may it be enabled
(``scripts/enable_locale.py`` in the API). Generating new strings for a reviewed locale makes it ``machine`` again.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Final, Literal, Self

from pydantic import BaseModel, model_validator

COMMAND_VERSION: Final = "1"
"""Bumped when the prompt, the validators or the glossary handling change in a way that makes older output differ."""

Status = Literal["machine", "reviewed"]


class LocaleReview(BaseModel):
    """The review state of one locale and how its strings were made."""

    status: Status
    reviewed_by: str | None = None
    reviewed_on: date | None = None
    model: str | None = None
    command_version: str

    @model_validator(mode="after")
    def _reviewed_names_who_and_when(self) -> Self:
        if self.status == "reviewed" and not (self.reviewed_by and self.reviewed_on):
            raise ValueError("a reviewed locale needs reviewed_by and reviewed_on")
        return self


class ReviewManifest(BaseModel):
    """Every locale that has an entry, by code."""

    locales: dict[str, LocaleReview] = {}


def load_manifest(path: Path) -> ReviewManifest:
    """Read the manifest at ``path``; a missing file is an empty manifest."""
    if not path.is_file():
        return ReviewManifest()
    return ReviewManifest.model_validate_json(path.read_text(encoding="utf-8"))


def save_manifest(path: Path, manifest: ReviewManifest) -> None:
    """Write ``manifest`` with sorted locales, two-space indent and one trailing newline."""
    ordered = ReviewManifest(locales=dict(sorted(manifest.locales.items())))
    path.write_text(ordered.model_dump_json(indent=2) + "\n", encoding="utf-8")


def record_generation(manifest: ReviewManifest, locale: str, *, model: str | None, generated: int) -> ReviewManifest:
    """Return ``manifest`` with ``locale`` after a run that made ``generated`` new strings.

    New machine text needs a review: the entry becomes ``machine`` with the model and the command version. A run
    that generated nothing leaves the entry as it is (a first run that generated nothing creates none).
    """
    if generated == 0:
        return manifest
    entry = LocaleReview(status="machine", model=model, command_version=COMMAND_VERSION)
    return ReviewManifest(locales={**manifest.locales, locale: entry})
