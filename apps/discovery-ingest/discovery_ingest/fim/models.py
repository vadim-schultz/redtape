"""Typed FIM Portal and LeiKa payloads: the steckbrief and the stammtext the enrich step reads."""

from __future__ import annotations

import json

from pydantic import ValidationError, model_validator

from discovery_ingest.json_types import JsonObject
from discovery_ingest.lenient import StrText, WireModel, first_present, text_or_none


class FimDocument(WireModel):
    """The text fields every FIM or LeiKa document shares: its title and short text."""

    titel: StrText = None
    kurztext: StrText = None


class Steckbrief(FimDocument):
    """A FIM steckbrief: the Leistungsschluessel and the label candidates."""

    leistungsschluessel: str
    title: StrText = None
    leistungsbezeichnung: StrText = None

    @model_validator(mode="before")
    @classmethod
    def _require_key(cls, data: object) -> object:
        """Require a non-blank string Leistungsschluessel; the key is kept as sent so fixtures compare it unchanged."""
        if isinstance(data, dict) and text_or_none(data.get("leistungsschluessel")) is None:
            raise ValueError("steckbrief missing leistungsschluessel")
        return data

    @classmethod
    def from_body(cls, body: bytes | None) -> Steckbrief | None:
        """Parse a steckbrief response body; ``None`` when it is missing, not UTF-8 JSON or not a JSON object."""
        if body is None:
            return None
        try:
            parsed = json.loads(body.decode())
        except ValueError:
            return None
        if not isinstance(parsed, dict):
            return None
        return cls.from_object(parsed)

    @classmethod
    def from_object(cls, payload: JsonObject) -> Steckbrief:
        """Validate a decoded steckbrief object; raise ``ValueError`` when the key is missing or blank."""
        try:
            return cls.model_validate(payload)
        except ValidationError as err:
            raise _plain_message(err) from err

    def label(self) -> str | None:
        """Return the first non-blank of ``title``, ``titel`` and ``leistungsbezeichnung``.

        The real response (probed 2026-10-26, decision D25) carries ``title`` and ``leistungsbezeichnung`` and no
        ``titel``; ``titel`` is the legacy shape of the early fixtures and is kept so older payloads still yield a label.
        """
        return first_present(self.title, self.titel, self.leistungsbezeichnung)


class Stammtext(FimDocument):
    """A LeiKa stammtext: the two path segments that address it."""

    redaktion_id: str
    leistung_id: str

    @model_validator(mode="before")
    @classmethod
    def _require_ids(cls, data: object) -> object:
        """Require both path segments, naming the first one that is missing or blank."""
        if isinstance(data, dict):
            if text_or_none(data.get("redaktion_id")) is None:
                raise ValueError("stammtext missing redaktion_id")
            if text_or_none(data.get("leistung_id")) is None:
                raise ValueError("stammtext missing leistung_id")
        return data

    @classmethod
    def from_object(cls, payload: JsonObject) -> Stammtext:
        """Validate a decoded stammtext object; raise ``ValueError`` naming the missing segment."""
        try:
            return cls.model_validate(payload)
        except ValidationError as err:
            raise _plain_message(err) from err


def _plain_message(err: ValidationError) -> ValueError:
    """Return a plain ``ValueError`` carrying the first validator message, without the pydantic wrapper."""
    return ValueError(str(err.errors()[0]["msg"]).removeprefix("Value error, "))
