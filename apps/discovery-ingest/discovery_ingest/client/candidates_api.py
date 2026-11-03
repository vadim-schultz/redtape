"""Candidate routes: mentions and edges, staged candidates, emit, sources and the taxonomy they are tagged with."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from discovery_ingest.candidate_sources import CandidateSourcePage, SourceQuery
from discovery_ingest.client.http_client import MachineHttpClient
from discovery_ingest.edges import EdgeItem, EdgesRequest, EdgesResponse
from discovery_ingest.emit_models import CandidatePage, EmitPreview, EmitRequest, EmitResponse
from discovery_ingest.extract.llm.taxonomy import Taxonomy
from discovery_ingest.mentions import MentionItem, MentionsRequest, MentionsResponse


class CandidatesAPI:
    """Record mentions and edges, list and emit candidates, and read the sources they were found on."""

    def __init__(self, http: MachineHttpClient) -> None:
        """Keep the shared HTTP client."""
        self._http = http

    def post_mentions(self, items: Sequence[MentionItem]) -> MentionsResponse:
        """Record up to 100 document mentions in one transaction."""
        body = MentionsRequest(items=list(items))
        return self._http.request_model(
            MentionsResponse, "POST", "/candidates/mentions", json=body.model_dump(mode="json")
        )

    def post_edges(self, items: Sequence[EdgeItem]) -> EdgesResponse:
        """Record up to 100 requirement edges; both endpoints must already be candidates (post mentions first)."""
        body = EdgesRequest(items=list(items))
        return self._http.request_model(EdgesResponse, "POST", "/candidates/edges", json=body.model_dump(mode="json"))

    def list_staged(self, *, min_mentions: int, limit: int, offset: int = 0) -> CandidatePage:
        """Return up to ``limit`` staged candidates from ``offset`` with at least ``min_mentions`` mentions, most mentioned first."""
        params: dict[str, str | int | list[str]] = {"status": "staged", "min_mentions": min_mentions, "limit": limit}
        if offset:
            params["offset"] = offset
        return self._http.request_model(CandidatePage, "GET", "/candidates/", params=params)

    def preview_emit(self, candidate_id: UUID) -> EmitPreview:
        """Return what emitting ``candidate_id`` would create; the route never writes."""
        return self._http.request_model(EmitPreview, "GET", f"/candidates/{candidate_id}/emit-preview")

    def emit(self, candidate_ids: Sequence[UUID]) -> EmitResponse:
        """Emit up to 50 candidates as pending suggestions; replays and duplicates are reported, not raised."""
        body = EmitRequest(candidate_ids=list(candidate_ids))
        return self._http.request_model(EmitResponse, "POST", "/candidates/emit", json=body.model_dump(mode="json"))

    def list_sources(self, query: SourceQuery) -> CandidateSourcePage:
        """List catalogue rows with candidate mentions and their newest snapshot url, one page of ``query``."""
        params: dict[str, str | int | list[str]] = {"offset": query.offset, "limit": query.limit}
        optional: dict[str, str | None] = {
            "host": query.host,
            "missing": query.missing,
            "candidate_id": None if query.candidate_id is None else str(query.candidate_id),
        }
        params |= {name: value for name, value in optional.items() if value is not None}
        if query.service_ids:
            params["catalogue_service_id"] = [str(service_id) for service_id in query.service_ids]
        return self._http.request_model(CandidateSourcePage, "GET", "/candidates/sources", params=params)

    def taxonomy(self) -> Taxonomy:
        """Return the closed domain and life-situation vocabulary workers tag pages with."""
        return self._http.request_model(Taxonomy, "GET", "/taxonomy")
