"""Builders for the public candidate API tests: one jurisdiction, procedures, candidates, mentions, edges."""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import TypeVar

from app.models.discovery import (
    CatalogueService,
    DiscoveryArtifact,
    DiscoveryArtifactKind,
    DiscoveryCandidateEdge,
    DiscoveryCandidateMention,
    DiscoveryCandidateStatus,
    DiscoveryDocumentCandidate,
    DiscoveryEdgeBasis,
    DiscoveryMentionRole,
    DiscoverySource,
)
from app.shared.object_store import ObjectStore
from sqlalchemy.orm import Session

from test_discovery_admin_api import _jurisdiction

BASE_TIME = datetime(2026, 10, 26, 12, 0, tzinfo=UTC)
HOUSING, MOVING = "home-and-housing", "moving-house"
Row = TypeVar("Row")


def _at(days_old: int) -> datetime:
    return BASE_TIME - timedelta(days=days_old)


class Scene:
    """Rows of one test, all in one jurisdiction; ``days_old`` makes row order explicit (the clock is frozen)."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.jurisdiction = _jurisdiction(session)

    def procedure(self, title: str = "Leistung", portal_url: str | None = None) -> CatalogueService:
        row = CatalogueService(
            source=DiscoverySource.GOVDATA,
            external_id=f"svc-{uuid.uuid4().hex[:8]}",
            jurisdiction_id=self.jurisdiction.id,
            title_i18n={"de": title},
            portal_url=portal_url,
            raw_payload={},
            pipeline_stage="T0",
        )
        return self._add(row)

    def candidate(
        self,
        key: str,
        *,
        title: dict[str, str] | None = None,
        status: DiscoveryCandidateStatus = DiscoveryCandidateStatus.STAGED,
    ) -> DiscoveryDocumentCandidate:
        row = DiscoveryDocumentCandidate(
            jurisdiction_id=self.jurisdiction.id, key=key, title_i18n=title or {"de": key}, status=status
        )
        return self._add(row)

    def mention(
        self,
        owner: DiscoveryDocumentCandidate,
        procedure: CatalogueService,
        *,
        role: DiscoveryMentionRole = DiscoveryMentionRole.REQUIRED,
        excerpt: str = "Bitte mitbringen",
        days_old: int = 0,
        categories: list[str] | None = None,
        extractor: str = "llm",
        category_confidence: float | None = None,
    ) -> DiscoveryCandidateMention:
        row = DiscoveryCandidateMention(
            candidate_id=owner.id,
            catalogue_service_id=procedure.id,
            role=role,
            excerpt=excerpt,
            source_field=f"details[{uuid.uuid4().hex[:8]}]",
            extractor=extractor,
            extractor_version="1",
            category_codes=categories,
            direct_category_confidence=category_confidence,
            created_at=_at(days_old),
        )
        return self._add(row)

    def edge(
        self,
        parent: DiscoveryDocumentCandidate,
        required: DiscoveryDocumentCandidate,
        procedure: CatalogueService | None = None,
        *,
        condition: str | None = None,
        is_optional: bool | None = None,
        excerpt: str = "Personalausweis erforderlich",
        days_old: int = 0,
    ) -> DiscoveryCandidateEdge:
        row = DiscoveryCandidateEdge(
            parent_candidate_id=parent.id,
            required_candidate_id=required.id,
            catalogue_service_id=(procedure or self.procedure()).id,
            condition=condition,
            is_optional=is_optional,
            excerpt=excerpt,
            basis=DiscoveryEdgeBasis.EXPLICIT,
            extractor="llm",
            extractor_version="1",
            created_at=_at(days_old),
        )
        return self._add(row)

    def artifact(
        self,
        procedure: CatalogueService,
        kind: DiscoveryArtifactKind,
        *,
        data: bytes | None = None,
        days_old: int = 0,
        content_type: str = "image/jpeg",
    ) -> DiscoveryArtifact:
        payload = data if data is not None else uuid.uuid4().bytes
        sha = hashlib.sha256(payload).hexdigest()
        row = DiscoveryArtifact(
            catalogue_service_id=procedure.id,
            kind=kind,
            storage_key=f"discovery/{procedure.id}/{kind.value}/{sha}.jpg",
            sha256=sha,
            content_type=content_type,
            byte_size=len(payload),
            source_url="https://example.gov/page",
            fetched_at=_at(days_old),
        )
        return self._add(row)

    def stored_screenshot(
        self, procedure: CatalogueService, store: ObjectStore, data: bytes, *, days_old: int = 0
    ) -> DiscoveryArtifact:
        """Add a screenshot row and put its bytes in ``store`` under the row's storage key."""
        row = self.artifact(procedure, DiscoveryArtifactKind.SCREENSHOT, data=data, days_old=days_old)
        store.put(row.storage_key, data, row.content_type)
        return row

    def scored(
        self,
        key: str,
        *,
        categories: Mapping[str, float] | None = None,
        title: dict[str, str] | None = None,
    ) -> DiscoveryDocumentCandidate:
        """Return a candidate whose every category scores exactly the given value: one direct-source mention each."""
        owner = self.candidate(key, title=title)
        for code, score in (categories or {}).items():
            self.mention(owner, self.procedure(), extractor="pvog", categories=[code], category_confidence=score)
        return owner

    def complete_candidate(self, key: str) -> DiscoveryDocumentCandidate:
        """Return a candidate with all four completeness flags: two categorised procedures, an edge, both artifacts."""
        first, second = self.procedure(), self.procedure()
        owner = self.candidate(key)
        for procedure in (first, second):
            self.mention(owner, procedure, categories=[HOUSING, MOVING])
        self.edge(owner, self.candidate(f"{key}-needs"))
        self.artifact(first, DiscoveryArtifactKind.HTML_SNAPSHOT, content_type="text/html")
        self.artifact(first, DiscoveryArtifactKind.SCREENSHOT)
        return owner

    def _add(self, row: Row) -> Row:
        self.session.add(row)
        self.session.flush()
        return row
