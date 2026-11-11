"""Read the Workers AI translator's JSON answer into one translated unit per asked unit."""

from __future__ import annotations

from pydantic import BaseModel, ValidationError

from discovery_ingest.translation.errors import UnusableOutputError
from discovery_ingest.translation.units import TranslationUnit


class AnswerUnit(BaseModel):
    """One translated unit as the model returns it."""

    key: str
    title: str
    description: str


class Answer(BaseModel):
    """The model's whole answer: the translated units."""

    units: list[AnswerUnit]


def parse_answer(parsed_json: str, asked: tuple[TranslationUnit, ...]) -> tuple[TranslationUnit, ...]:
    """Return one translated unit per asked unit, in order; raise :class:`UnusableOutputError` for anything else."""
    try:
        answer = Answer.model_validate_json(parsed_json)
    except ValidationError as err:
        raise UnusableOutputError("the model answer does not follow the translation schema") from err
    by_key = {unit.key: unit for unit in answer.units}
    missing = [unit.key for unit in asked if unit.key not in by_key]
    if missing:
        raise UnusableOutputError(f"the model answered {len(answer.units)} of {len(asked)} units; missing {missing}")
    return tuple(TranslationUnit(u.key, by_key[u.key].title, by_key[u.key].description) for u in asked)
