"""Page-level completeness (D6): a ``catalogue_service_id``-keyed count of chips, for queue ordering only.

Simpler than the per-candidate ``candidate_completeness_flags`` subquery, by design: ``DiscoveryCandidateMention``,
``DiscoveryCandidateEdge`` and ``DiscoveryArtifact`` all carry ``catalogue_service_id`` directly, so each flag is a
plain existence/non-empty check against that column — no join through ``DiscoveryDocumentCandidate`` and no
consensus-threshold ``axis_acceptance`` logic. This feeds only the task queue's claim-order tie-break within a
priority tier (chapter 4); it is not a redefinition of "complete" and never touches the canonical per-candidate
``completeness_subquery``/``completeness_order`` used by candidate-browsing lists.
"""

from __future__ import annotations

from functools import reduce
from operator import add

from sqlalchemy import ColumnElement, Integer, cast, func, select, union
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.sql.expression import Select, Subquery

from app.models.discovery import DiscoveryArtifact as Artifact
from app.models.discovery import DiscoveryArtifactKind
from app.models.discovery import DiscoveryCandidateEdge as Edge
from app.models.discovery import DiscoveryCandidateMention as Mention

FLAG_NAMES = ("has_domain", "has_situation", "has_edges", "has_snapshot", "has_screenshot")


def _code_flag(column: InstrumentedAttribute[list[str] | None]) -> Subquery:
    """Pages with a mention whose ``column`` array holds at least one code."""
    return select(Mention.catalogue_service_id).where(func.cardinality(column) > 0).distinct().subquery()


def _edge_flag() -> Subquery:
    """Pages with at least one staged dependency edge."""
    return select(Edge.catalogue_service_id).distinct().subquery()


def _artifact_flag(kind: DiscoveryArtifactKind) -> Subquery:
    """Pages with a stored artifact of ``kind``."""
    return select(Artifact.catalogue_service_id).where(Artifact.kind == kind).distinct().subquery()


def _with_flags(stmt: Select, holders: tuple[Subquery, ...], key: ColumnElement) -> Select:
    for holder in holders:
        stmt = stmt.outerjoin(holder, holder.c.catalogue_service_id == key)
    return stmt


def page_completeness_subquery() -> Subquery:
    """Return ``(catalogue_service_id, page_completeness)`` for every page with at least one chip.

    A page with no mentions, edges or artifacts at all has no row here; callers outer-join on
    ``catalogue_service_id`` and ``coalesce(page_completeness, 0)`` to cover it.
    """
    holders = (
        _code_flag(Mention.domain_codes),
        _code_flag(Mention.situation_codes),
        _edge_flag(),
        _artifact_flag(DiscoveryArtifactKind.HTML_SNAPSHOT),
        _artifact_flag(DiscoveryArtifactKind.SCREENSHOT),
    )
    ids = union(*(select(holder.c.catalogue_service_id) for holder in holders)).subquery()
    key = ids.c.catalogue_service_id
    flags = [
        holder.c.catalogue_service_id.is_not(None).label(name) for name, holder in zip(FLAG_NAMES, holders, strict=True)
    ]
    joined = _with_flags(select(key.label("catalogue_service_id"), *flags), holders, key).subquery()
    total = reduce(add, (cast(joined.c[name], Integer) for name in FLAG_NAMES))
    return select(joined.c.catalogue_service_id, total.label("page_completeness")).subquery()
