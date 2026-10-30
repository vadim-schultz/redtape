"""Filter of the candidate sources listing."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import ColumnElement, select

from app.features.discovery.repository.artifact_listing import url_host
from app.models.discovery import DiscoveryCandidateMention


@dataclass(frozen=True, slots=True)
class CandidateSourceFilter:
    """Narrowing of the sources listing: a missing screenshot, the snapshot host, one candidate, chosen procedures."""

    missing_screenshot: bool = False
    host: str | None = None
    candidate_id: UUID | None = None
    service_ids: Sequence[UUID] = ()

    def conditions(
        self, procedure: ColumnElement[UUID], source_url: ColumnElement[str], has_screenshot: ColumnElement[bool]
    ) -> list[ColumnElement[bool]]:
        """Return the where-clauses of the filters that are set, over the listing's columns."""
        mentioning = select(DiscoveryCandidateMention.catalogue_service_id).where(
            DiscoveryCandidateMention.candidate_id == self.candidate_id
        )
        wanted = [
            (self.missing_screenshot, ~has_screenshot),
            (self.host is not None, url_host(source_url) == (self.host or "").lower()),
            (self.candidate_id is not None, procedure.in_(mentioning)),
            (bool(self.service_ids), procedure.in_(list(self.service_ids))),
        ]
        return [condition for active, condition in wanted if active]
