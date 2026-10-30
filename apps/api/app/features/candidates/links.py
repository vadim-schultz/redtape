"""Neighbours and sources of a candidate: edges merged per neighbour, mentions reduced per procedure."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlparse
from uuid import UUID

from app.features.candidates.card_builder import CardContext
from app.features.candidates.localize import localized
from app.features.candidates.roles import role_rank
from app.features.discovery.repository import EdgeRow
from app.features.discovery.repository.candidate_listing import CandidateMentionRow
from app.models.discovery import DiscoveryDocumentCandidate as Candidate
from app.schema.candidate import CandidateNeighbour, CandidateSource
from app.shared.locale import ResolvedLocale

NEIGHBOUR_CAP = 50
WEB_SCHEMES = ("http", "https")
Far = Callable[[EdgeRow], Candidate]


@dataclass(frozen=True, slots=True)
class NeighbourSide:
    """The neighbours on one side of a candidate and whether the cap cut some off."""

    items: list[CandidateNeighbour]
    truncated: bool


def _merged(group: list[EdgeRow], far: Far, context: CardContext) -> CandidateNeighbour:
    oldest, neighbour = group[0], far(group[0])
    description, _source = context.describe(neighbour.id)
    return CandidateNeighbour(
        id=neighbour.id,
        title=localized(neighbour.title_i18n, context.locale),
        description=description,
        condition=oldest.edge.condition,
        is_optional=all(row.edge.is_optional is True for row in group),
        excerpt=oldest.edge.excerpt,
        basis=oldest.edge.basis,
        procedure_title=localized(oldest.procedure.title_i18n, context.locale),
    )


def _grouped(edges: Sequence[EdgeRow], far: Far) -> list[list[EdgeRow]]:
    groups: dict[UUID, list[EdgeRow]] = {}
    for row in edges:
        groups.setdefault(far(row).id, []).append(row)
    return list(groups.values())


def merged_neighbours(edges: Sequence[EdgeRow], far: Far, context: CardContext) -> NeighbourSide:
    """Merge ``edges`` (oldest first) per far-end candidate, ordered by title then id and capped at 50."""
    merged = [_merged(group, far, context) for group in _grouped(edges, far)]
    merged.sort(key=lambda neighbour: (neighbour.title.casefold(), neighbour.id))
    return NeighbourSide(merged[:NEIGHBOUR_CAP], len(merged) > NEIGHBOUR_CAP)


def public_url(url: str | None) -> str | None:
    """Return ``url`` only when it is an http or https URL; anything else (``javascript:``, ``data:``) is hidden."""
    return url if url and urlparse(url).scheme in WEB_SCHEMES else None


def _source(row: CandidateMentionRow, locale: ResolvedLocale) -> CandidateSource:
    mention = row.mention
    return CandidateSource(
        procedure_title=localized(row.procedure.title_i18n, locale),
        portal_url=public_url(row.procedure.portal_url),
        role=mention.role,
        excerpt=mention.excerpt,
        condition=mention.condition,
        is_optional=mention.is_optional is True,
    )


def _mention_rank(row: CandidateMentionRow) -> tuple[int, datetime, UUID]:
    return role_rank(row.mention.role), row.mention.created_at, row.mention.id


def sources_of(mentions: Sequence[CandidateMentionRow], locale: ResolvedLocale) -> list[CandidateSource]:
    """Return the best mention (role, then oldest) of each procedure, best procedures first."""
    best: dict[UUID, CandidateMentionRow] = {}
    for row in sorted(mentions, key=_mention_rank):
        best.setdefault(row.procedure.id, row)
    return [_source(row, locale) for row in best.values()]
