"""The review manifest (``translations/review.json``): which locales may be enabled, and on whose word.

Written by ``python -m discovery_ingest i18n translate-ui`` (status ``machine``) and edited by hand when a native review
or an operator's acceptance is recorded. Seeds read it but never enable a locale; ``enable_locale.py`` enables only a
``reviewed`` or a ``machine_accepted`` one.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Final, Literal, Self

from pydantic import BaseModel, model_validator

MANIFEST_FILE: Final = "review.json"
REVIEW_PATH: Final = Path(__file__).resolve().parent / "translations" / MANIFEST_FILE


class LocaleReview(BaseModel):
    """The review state of one locale and how its strings were made."""

    status: Literal["machine", "reviewed", "machine_accepted"]
    reviewed_by: str | None = None
    reviewed_on: date | None = None
    accepted_by: str | None = None
    accepted_on: date | None = None
    model: str | None = None
    command_version: str

    @model_validator(mode="after")
    def _decision_names_who_and_when(self) -> Self:
        if self.status == "reviewed" and not (self.reviewed_by and self.reviewed_on):
            raise ValueError("a reviewed locale needs reviewed_by and reviewed_on")
        if self.status == "machine_accepted" and not (self.accepted_by and self.accepted_on):
            raise ValueError("a machine_accepted locale needs accepted_by and accepted_on")
        return self


class ReviewManifest(BaseModel):
    """Every locale that has an entry, by code."""

    locales: dict[str, LocaleReview] = {}


def load_review_manifest(path: Path = REVIEW_PATH) -> ReviewManifest:
    """Read the manifest at ``path``; a missing file is an empty manifest."""
    if not path.is_file():
        return ReviewManifest()
    return ReviewManifest.model_validate_json(path.read_text(encoding="utf-8"))
