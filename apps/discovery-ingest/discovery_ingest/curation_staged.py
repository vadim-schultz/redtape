"""The staged candidates a curation file is resolved against, indexed by id and by key (chapter 11)."""

from __future__ import annotations

from collections.abc import Iterable
from difflib import get_close_matches
from uuid import UUID

from discovery_ingest.api_client import DiscoveryMachineClient
from discovery_ingest.emit_models import CandidateSummary
from discovery_ingest.extract.llm.normalise import name_slug
from discovery_ingest.mentions import MentionRole

PAGE_SIZE = 100
"""The most the candidates route serves in one page."""
ROLE_ORDER: tuple[MentionRole, ...] = ("required", "form", "issued")


def title_of(candidate: CandidateSummary) -> str:
    """Return the German title of ``candidate``, or its first title."""
    return candidate.title_i18n.get("de") or next(iter(candidate.title_i18n.values()))


class StagedIndex:
    """Staged candidates looked up by id, or by title slug within a jurisdiction."""

    def __init__(self, candidates: Iterable[CandidateSummary]) -> None:
        self._by_id = {c.id: c for c in candidates}
        self._by_key = {(c.jurisdiction_id, c.key): c for c in self._by_id.values()}

    @classmethod
    def fetch(cls, client: DiscoveryMachineClient) -> StagedIndex:
        """Read every staged candidate, one route page at a time."""
        found: list[CandidateSummary] = []
        while True:
            page = client.list_staged_candidates(min_mentions=0, limit=PAGE_SIZE, offset=len(found))
            found += page.items
            if not page.items or len(found) >= page.total:
                return cls(found)

    def get(self, candidate_id: UUID) -> CandidateSummary | None:
        """Return the staged candidate with ``candidate_id``, if any."""
        return self._by_id.get(candidate_id)

    def named(self, jurisdiction_id: UUID, title: str) -> CandidateSummary | None:
        """Return the staged candidate whose key is the slug of ``title`` in the jurisdiction, if any."""
        return self._by_key.get((jurisdiction_id, name_slug(title)))

    def closest_title(self, jurisdiction_id: UUID, title: str) -> str | None:
        """Return the staged title in the jurisdiction most like ``title``, if any is alike."""
        titles = [title_of(c) for c in self._by_id.values() if c.jurisdiction_id == jurisdiction_id]
        close = get_close_matches(title, titles, n=1, cutoff=0.6)
        return close[0] if close else None

    def strongest_role(self, candidate_id: UUID) -> MentionRole:
        """Return the strongest role (required, form, issued) a staged candidate was mentioned in."""
        roles = self._by_id[candidate_id].roles
        return next((role for role in ROLE_ORDER if role in roles), ROLE_ORDER[0])
