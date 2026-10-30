"""Checks of a curation file against the live vocabulary, the staged candidates and the stored pages (chapter 11)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from uuid import UUID

from discovery_ingest.candidate_sources import CandidateSourceRead
from discovery_ingest.curation import CurationCandidate, CurationFile
from discovery_ingest.curation_staged import StagedIndex, title_of
from discovery_ingest.emit_models import CandidateSummary
from discovery_ingest.extract.llm.normalise import name_slug, normalise
from discovery_ingest.extract.llm.taxonomy import Taxonomy

Procedures = Mapping[UUID, list[CandidateSourceRead]]
PageText = Callable[[CandidateSourceRead], str | None]


def code_problems(file: CurationFile, taxonomy: Taxonomy) -> list[str]:
    """Return a line for each domain or situation code that the closed vocabulary does not hold."""
    axes = (("domain_codes", taxonomy.domain_codes), ("situation_codes", taxonomy.situation_codes))
    return [
        f"{c.title_de!r} {field}: unknown code {code!r}"
        for c in file.candidates
        for field, known in axes
        for code in getattr(c, field)
        if code not in known
    ]


def _nearest(staged: StagedIndex, jurisdiction_id: UUID, title: str) -> str:
    closest = staged.closest_title(jurisdiction_id, title)
    return f"; closest staged title: {closest!r}" if closest else "; no staged title is alike"


def _title_problems(entry: CurationCandidate, home: CandidateSummary) -> list[str]:
    if name_slug(entry.title_de) == home.key:
        return []
    return [f"{entry.title_de!r} title_de: does not match the staged candidate {title_of(home)!r}"]


def _procedure_problems(entry: CurationCandidate, procedures: Procedures) -> list[str]:
    if entry.catalogue_service_id in {s.catalogue_service_id for s in procedures[entry.candidate_id]}:
        return []
    return [
        f"{entry.title_de!r} catalogue_service_id: {entry.catalogue_service_id} is not a procedure of the candidate"
    ]


def _entry_problems(entry: CurationCandidate, staged: StagedIndex, procedures: Procedures) -> list[str]:
    home = staged.get(entry.candidate_id)
    if home is None:
        return [f"{entry.title_de!r} candidate_id: {entry.candidate_id} is not a staged candidate"]
    neighbours = _neighbour_problems(entry, staged, home.jurisdiction_id)
    return _title_problems(entry, home) + _procedure_problems(entry, procedures) + neighbours


def _neighbour_problems(entry: CurationCandidate, staged: StagedIndex, jurisdiction_id: UUID) -> list[str]:
    unknown = [e for _, _, e in entry.edges() if not e.create and not staged.named(jurisdiction_id, e.title_de)]
    return [
        f"{entry.title_de!r} edge {e.title_de!r}: not a staged candidate{_nearest(staged, jurisdiction_id, e.title_de)}"
        for e in unknown
    ]


def title_problems(file: CurationFile, staged: StagedIndex, procedures: Procedures) -> list[str]:
    """Return a line for each entry or neighbour that does not resolve to a staged candidate, or sits on a foreign procedure."""
    return [p for c in file.candidates for p in _entry_problems(c, staged, procedures)]


def grounding_problems(file: CurationFile, procedures: Procedures, page_text: PageText) -> list[str]:
    """Return a line for each excerpt that is not a substring of its procedure's cleaned page text (both normalised)."""
    problems: list[str] = []
    for entry in file.candidates:
        source = next(s for s in procedures[entry.candidate_id] if s.catalogue_service_id == entry.catalogue_service_id)
        text = page_text(source)
        problems += _missing_page(entry) if text is None else _ungrounded(entry, normalise(text))
    return problems


def _missing_page(entry: CurationCandidate) -> list[str]:
    return [f"{entry.title_de!r}: no html_snapshot is stored for procedure {entry.catalogue_service_id}"]


def _ungrounded(entry: CurationCandidate, haystack: str) -> list[str]:
    return [
        f"{entry.title_de!r} edge {e.title_de!r} excerpt: not found in the cleaned page text"
        for _, _, e in entry.edges()
        if normalise(e.excerpt) not in haystack
    ]
