"""Read models of a candidate's translated document: the blocks of its best page, and the codes of the answers without them."""

from __future__ import annotations

import enum

from pydantic import BaseModel, ConfigDict

from app.schema.translation.snapshot_machine import SnapshotBlock


class DocumentTranslationCode(enum.StrEnum):
    """Why a candidate's document has no blocks to show: the 404 answers of the document route."""

    CANDIDATE_NOT_FOUND = "candidate_not_found"
    NO_DOCUMENT = "no_document"
    TRANSLATION_PENDING = "translation_pending"
    SKIPPED = "skipped"


class DocumentTranslationRead(BaseModel):
    """The translated blocks of a candidate's best page in one locale.

    ``source_url`` is the page's web link, ``null`` when the procedure has none. ``stale`` is true when the page changed
    after the translation was made. ``truncated`` is true when the German text was cut before it was translated.
    """

    model_config = ConfigDict(from_attributes=False)

    locale: str
    source_url: str | None
    truncated: bool
    stale: bool
    blocks: list[SnapshotBlock]


class DocumentTranslationError(BaseModel):
    """The 404 body of the document route: a ``code``, and the skip ``reason`` when the page was skipped."""

    model_config = ConfigDict(from_attributes=False)

    code: DocumentTranslationCode
    reason: str | None = None
