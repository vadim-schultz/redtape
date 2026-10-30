"""The pure planner: a validated curation file becomes the mentions and edges to post (chapter 11)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict

from discovery_ingest.curation import MANUAL_EXTRACTOR, MANUAL_VERSION, CurationCandidate, CurationFile
from discovery_ingest.curation_staged import StagedIndex
from discovery_ingest.edges import EdgeItem
from discovery_ingest.extract.llm.normalise import name_slug
from discovery_ingest.mentions import MentionItem


class _Manual(TypedDict):
    extractor: str
    extractor_version: str


MANUAL: _Manual = {"extractor": MANUAL_EXTRACTOR, "extractor_version": MANUAL_VERSION}


@dataclass(frozen=True, slots=True)
class CandidateLine:
    """What one file entry writes: the title, the codes it assigns and the edges it states."""

    title: str
    tags: int
    edges: int


@dataclass(frozen=True, slots=True)
class CurationPlan:
    """Everything a file posts: mentions first, then edges, and one report line per candidate."""

    mentions: list[MentionItem]
    edges: list[EdgeItem]
    lines: list[CandidateLine]


def _tag_mentions(entry: CurationCandidate, staged: StagedIndex) -> list[MentionItem]:
    """Return the one ``manual:tags`` mention of an entry that assigns codes; its excerpt is the first edge's or the note."""
    if not entry.tag_count:
        return []
    excerpt = next((e.excerpt for _, _, e in entry.edges()), entry.tag_note or "")
    return [
        MentionItem(
            catalogue_service_id=entry.catalogue_service_id,
            title_i18n={"de": entry.title_de},
            role=staged.strongest_role(entry.candidate_id),
            excerpt=excerpt,
            source_field="manual:tags",
            **MANUAL,
            domain_codes=entry.domain_codes or None,
            situation_codes=entry.situation_codes or None,
        )
    ]


def _neighbour_mentions(entry: CurationCandidate, staged: StagedIndex) -> list[MentionItem]:
    """Return a ``manual:neighbour`` mention for each neighbour marked ``create`` that is not staged yet."""
    home = staged.get(entry.candidate_id)
    missing = [
        e for _, _, e in entry.edges() if e.create and home and not staged.named(home.jurisdiction_id, e.title_de)
    ]
    return [
        MentionItem(
            catalogue_service_id=entry.catalogue_service_id,
            title_i18n={"de": e.title_de},
            role="required",
            excerpt=e.excerpt,
            source_field="manual:neighbour",
            **MANUAL,
        )
        for e in missing
    ]


def _edge_items(entry: CurationCandidate) -> list[EdgeItem]:
    return [
        EdgeItem(
            catalogue_service_id=entry.catalogue_service_id,
            parent_title_i18n={"de": parent},
            required_title_i18n={"de": required},
            basis="explicit",
            condition=e.condition,
            is_optional=e.is_optional,
            excerpt=e.excerpt,
            **MANUAL,
        )
        for parent, required, e in entry.edges()
    ]


def _distinct(mentions: list[MentionItem]) -> list[MentionItem]:
    """Keep the first mention of each (procedure, title, role, source field): the API's identity."""
    keyed = {
        (m.catalogue_service_id, name_slug(m.title_i18n["de"]), m.role, m.source_field): m for m in reversed(mentions)
    }
    return list(reversed(keyed.values()))


def plan_curation(file: CurationFile, staged: StagedIndex) -> CurationPlan:
    """Return the mentions (tags, then missing neighbours), edges and report lines of ``file``; nothing is posted."""
    mentions = [m for c in file.candidates for m in _tag_mentions(c, staged) + _neighbour_mentions(c, staged)]
    edges = [e for c in file.candidates for e in _edge_items(c)]
    lines = [CandidateLine(c.title_de, c.tag_count, len(c.edges())) for c in file.candidates]
    return CurationPlan(_distinct(mentions), edges, lines)
