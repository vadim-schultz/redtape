"""The Azure request and answer for one target: inputs cut into requests, answers read back by position."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final, Literal

from pydantic import BaseModel, Field, TypeAdapter, ValidationError

from discovery_ingest.translation.errors import PermanentError, UnusableOutputError
from discovery_ingest.translation.units import TranslationUnit

MAX_INPUTS_PER_REQUEST: Final = 500
MAX_CHARS_PER_REQUEST: Final = 40_000
"""Ceilings of one request, under the service's 1,000 inputs and 50,000 characters (counted across targets)."""
TEXT_TYPE: Final = "plain"
FieldName = Literal["title", "description"]


@dataclass(frozen=True, slots=True)
class Piece:
    """One text sent as one input: the position of its unit in the batch, its field, and the text."""

    unit: int
    field: FieldName
    text: str


class _Translation(BaseModel):
    text: str
    to: str | None = None


class _Answer(BaseModel):
    translations: list[_Translation] = Field(min_length=1)


_ANSWERS: Final = TypeAdapter(list[_Answer])


def pieces_of(units: Sequence[TranslationUnit]) -> list[Piece]:
    """Return one piece per non-blank title and description, in the order of the units."""
    pieces = [Piece(n, field, text) for n, unit in enumerate(units) for field, text in _fields(unit)]
    return [piece for piece in pieces if piece.text.strip()]


def _fields(unit: TranslationUnit) -> tuple[tuple[FieldName, str], ...]:
    return (("title", unit.title), ("description", unit.description))


def characters_of(pieces: Sequence[Piece]) -> int:
    """Return the characters of the texts of ``pieces``."""
    return sum(len(piece.text) for piece in pieces)


def chunks_of(pieces: Sequence[Piece]) -> list[list[Piece]]:
    """Cut ``pieces``, in order, into requests of at most 500 inputs and 40,000 characters each."""
    chunks: list[list[Piece]] = []
    for piece in map(_within_limit, pieces):
        if chunks and _fits(chunks[-1], piece):
            chunks[-1].append(piece)
        else:
            chunks.append([piece])
    return chunks


def _within_limit(piece: Piece) -> Piece:
    if len(piece.text) > MAX_CHARS_PER_REQUEST:
        raise PermanentError("a text is longer than one request may carry; nothing was sent")
    return piece


def _fits(chunk: Sequence[Piece], piece: Piece) -> bool:
    return len(chunk) < MAX_INPUTS_PER_REQUEST and characters_of(chunk) + len(piece.text) <= MAX_CHARS_PER_REQUEST


def request_body(chunk: Sequence[Piece], source: str, target: str) -> dict[str, list[dict[str, object]]]:
    """Return one request body: each input names the source, the plain text type and exactly one target."""
    inputs: list[dict[str, object]] = [
        {"text": piece.text, "language": source, "textType": TEXT_TYPE, "targets": [{"language": target}]}
        for piece in chunk
    ]
    return {"inputs": inputs}


def read_answers(body: object, chunk: Sequence[Piece], target: str) -> list[str]:
    """Return the translation of each input of ``chunk``, by position; any other shape or length is unusable output."""
    try:
        answers = _ANSWERS.validate_python(body)
    except ValidationError as err:
        raise UnusableOutputError("the Azure answer does not follow the translate schema") from err
    if len(answers) != len(chunk):
        raise UnusableOutputError(f"the Azure answer has {len(answers)} of {len(chunk)} translations")
    return [_text_for(answer, target) for answer in answers]


def _text_for(answer: _Answer, target: str) -> str:
    first = answer.translations[0]
    if first.to not in (None, target):
        raise UnusableOutputError(f"the Azure answer is for {first.to!r}, not for {target!r}")
    return first.text
