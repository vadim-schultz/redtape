"""The name rules of grounding: which document names are dropped, and why."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from discovery_ingest.extract.llm.data_fields import is_data_field
from discovery_ingest.extract.llm.generic_names import is_generic_name
from discovery_ingest.extract.llm.ground_state import Tally
from discovery_ingest.extract.llm.normalise import name_slug
from discovery_ingest.extract.llm.schema import DocumentItem
from discovery_ingest.harvest.noise import is_noise

Seen = set[tuple[str, str]]
"""The ``(name slug, role)`` pairs kept so far."""


def _is_noise(document: DocumentItem, seen: Seen) -> bool:
    return is_noise(document.name) or not name_slug(document.name)


def _is_data_field(document: DocumentItem, seen: Seen) -> bool:
    return is_data_field(document.name)


def _is_generic_name(document: DocumentItem, seen: Seen) -> bool:
    return is_generic_name(document.name)


def _is_repeat(document: DocumentItem, seen: Seen) -> bool:
    return (name_slug(document.name), document.role) in seen


NAME_REJECTIONS: tuple[tuple[str, Callable[[DocumentItem, Seen], bool]], ...] = (
    ("noise", _is_noise),
    ("data_field", _is_data_field),
    ("generic_name", _is_generic_name),
    ("duplicate", _is_repeat),
)


def _name_verdict(document: DocumentItem, seen: Seen) -> str | None:
    return next((reason for reason, rejects in NAME_REJECTIONS if rejects(document, seen)), None)


def keep_names(documents: Sequence[DocumentItem], tally: Tally) -> list[DocumentItem]:
    """Drop noise, data fields, generic names and repeats of one ``(slug, role)``, keeping the first."""
    seen: Seen = set()
    kept: list[DocumentItem] = []
    for document in documents:
        verdict = _name_verdict(document, seen)
        if verdict is not None:
            tally.lose(verdict, document)
            continue
        seen.add((name_slug(document.name), document.role))
        kept.append(document)
    return kept
