"""The four completeness flags of a candidate as one selectable subquery (D1).

Each flag is "the candidate has a row in a set of candidate ids": an edge end, a mention whose procedure
holds an artifact, an accepted code. The sets are joined once, so the planner hashes them instead of running
a correlated ``EXISTS`` per candidate and per reference.
"""

from __future__ import annotations

from sqlalchemy import select, union
from sqlalchemy.sql.expression import Select, Subquery

from app.features.discovery.repository.candidate_completeness_tags import category_acceptance
from app.models.discovery import DiscoveryArtifact as Artifact
from app.models.discovery import DiscoveryArtifactKind
from app.models.discovery import DiscoveryCandidateEdge as Edge
from app.models.discovery import DiscoveryCandidateMention as Mention
from app.models.discovery import DiscoveryDocumentCandidate as Candidate

# Four flags by decision D-R4 (2026-11-06). The five-flag split (has_domain, has_situation) stays retired; the parity
# test in tests/test_candidate_completeness.py pins the public order and the complete value to this rule.
FLAG_NAMES = ("has_category", "has_edges", "has_snapshot", "has_screenshot")


def _edge_flag() -> Subquery:
    parents = select(Edge.parent_candidate_id.label("candidate_id"))
    required = select(Edge.required_candidate_id.label("candidate_id"))
    return union(parents, required).subquery()


def _artifact_flag(kind: DiscoveryArtifactKind) -> Subquery:
    same_procedure = Artifact.catalogue_service_id == Mention.catalogue_service_id
    stmt = select(Mention.candidate_id).join(Artifact, same_procedure).where(Artifact.kind == kind)
    return stmt.distinct().subquery()


def _with_flags(stmt: Select, holders: tuple[Subquery, ...]) -> Select:
    for holder in holders:
        stmt = stmt.outerjoin(holder, holder.c.candidate_id == Candidate.id)
    return stmt


def flags_subquery() -> Subquery:
    """Return one row per candidate: the flags in ``FLAG_NAMES`` order and the accepted category codes."""
    category = category_acceptance()
    snapshot, screenshot = (
        _artifact_flag(DiscoveryArtifactKind.HTML_SNAPSHOT),
        _artifact_flag(DiscoveryArtifactKind.SCREENSHOT),
    )
    holders = (category, _edge_flag(), snapshot, screenshot)
    flags = [holder.c.candidate_id.is_not(None).label(name) for name, holder in zip(FLAG_NAMES, holders, strict=True)]
    codes = (category.c.codes.label("accepted_category_codes"),)
    return _with_flags(select(Candidate.id.label("candidate_id"), *flags, *codes), holders).subquery()
