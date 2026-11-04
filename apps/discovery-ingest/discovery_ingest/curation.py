"""The curation file: the manual tags and edges a curator reviewed, as strict models (chapter 11)."""

from __future__ import annotations

from collections import Counter
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from discovery_ingest.extract.llm.normalise import name_slug
from discovery_ingest.mentions import MAX_CATEGORY_CODES, MAX_CONDITION_LENGTH, Code
from discovery_ingest.pvog.category_mapping import categories_for_legacy_codes

_LEGACY_AXES: tuple[tuple[Literal["domain", "life_situation"], str], ...] = (
    ("domain", "domain_codes"),
    ("life_situation", "situation_codes"),
)


def _canonical_for_legacy(title: object, axis: Literal["domain", "life_situation"], code: str) -> tuple[str, ...]:
    """Return the canonical categories for one legacy code; a code with none refuses the entry."""
    categories = categories_for_legacy_codes(axis, (code,))
    if not categories:
        raise ValueError(f"{title!r}: unknown {axis} code {code!r}")
    return categories


MANUAL_EXTRACTOR = "manual"
"""The extractor name of every row the tool writes; the API's manual override keys on the same value."""
MANUAL_VERSION = "1"
MAX_CANDIDATES = 8
MAX_EDGES = 60
MAX_TITLE_LENGTH = 120
MAX_EXCERPT_LENGTH = 300

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_TITLE_LENGTH)]
Excerpt = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_EXCERPT_LENGTH)]
Condition = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_CONDITION_LENGTH)]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CurationEdge(_Strict):
    """The other end of one edge: a document, the verbatim sentence that states it and the edge's qualifiers."""

    title_de: Title
    excerpt: Excerpt
    condition: Condition | None = None
    is_optional: bool = False
    create: bool = False


class CurationCandidate(_Strict):
    """One candidate to complete: its tags on a procedure and the documents it requires or is required by."""

    candidate_id: UUID
    catalogue_service_id: UUID
    title_de: Title
    category_codes: list[Code] = Field(default_factory=list, max_length=MAX_CATEGORY_CODES)
    tag_note: Excerpt | None = None
    requires: list[CurationEdge] = Field(default_factory=list)
    required_by: list[CurationEdge] = Field(default_factory=list)

    @property
    def tag_count(self) -> int:
        """Return how many codes the entry assigns."""
        return len(self.category_codes)

    def edges(self) -> list[tuple[str, str, CurationEdge]]:
        """Return ``(parent title, required title, edge)``: ``requires`` makes this candidate the parent."""
        own = self.title_de
        return [(own, e.title_de, e) for e in self.requires] + [(e.title_de, own, e) for e in self.required_by]

    @model_validator(mode="after")
    def _codes_have_a_reason(self) -> Self:
        if self.tag_count and not self.tag_note:
            raise ValueError(f"{self.title_de!r}: tag_note is required when codes are given")
        return self

    @model_validator(mode="before")
    @classmethod
    def _translate_legacy_axes(cls, value: object) -> object:
        """Translate compatibility-axis fields before validating manual category codes."""
        if not isinstance(value, dict):
            return value
        legacy_fields = {"domain_codes", "situation_codes"}
        if not legacy_fields & value.keys():
            return value
        if "category_codes" in value:
            raise ValueError("legacy domain/situation fields cannot be combined with category_codes")
        categories = [
            category
            for axis, field_name in _LEGACY_AXES
            for code in value.get(field_name) or ()
            for category in _canonical_for_legacy(value.get("title_de"), axis, code)
        ]
        translated = {key: item for key, item in value.items() if key not in legacy_fields}
        translated["category_codes"] = list(dict.fromkeys(categories))
        return translated

    @model_validator(mode="after")
    def _no_self_edge(self) -> Self:
        for parent, required, _ in self.edges():
            if name_slug(parent) == name_slug(required):
                raise ValueError(f"{self.title_de!r}: an edge from {parent!r} to itself")
        return self


class CurationFile(_Strict):
    """A reviewed curation file: at most eight candidates and sixty edges, signed by the curator."""

    version: Literal[1]
    curator: Title
    candidates: list[CurationCandidate] = Field(min_length=1, max_length=MAX_CANDIDATES)

    def all_edges(self) -> list[tuple[CurationCandidate, str, str, CurationEdge]]:
        """Return every edge of the file with its candidate, parent title and required title."""
        return [(c, parent, required, e) for c in self.candidates for parent, required, e in c.edges()]

    @model_validator(mode="after")
    def _edges_are_bounded_and_distinct(self) -> Self:
        edges = self.all_edges()
        if len(edges) > MAX_EDGES:
            raise ValueError(f"{len(edges)} edges; a file holds at most {MAX_EDGES}")
        if repeated := _repeated(edges):
            raise ValueError(f"duplicate edges: {', '.join(repeated)}")
        return self


def _repeated(edges: list[tuple[CurationCandidate, str, str, CurationEdge]]) -> list[str]:
    """Return ``parent requires required`` for each edge stated twice on one procedure, in file order."""
    keyed = [((c.catalogue_service_id, name_slug(p), name_slug(r)), f"{p!r} requires {r!r}") for c, p, r, _ in edges]
    seen = Counter(key for key, _ in keyed)
    return list(dict.fromkeys(text for key, text in keyed if seen[key] > 1))
