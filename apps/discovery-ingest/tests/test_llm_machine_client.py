"""The machine client methods llm_extract needs: edges, and the unknown-code count of a mention batch (chapter E6)."""

from __future__ import annotations

import uuid

import pytest
from discovery_ingest.client import DiscoveryMachineApiError
from discovery_ingest.edges import EdgeItem
from discovery_ingest.mentions import MentionItem, MentionsResponse

from llm_worker_fakes import LlmApi

CATALOGUE_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


def _edge() -> EdgeItem:
    return EdgeItem(
        catalogue_service_id=CATALOGUE_ID,
        parent_title_i18n={"de": "Meldebescheinigung"},
        required_title_i18n={"de": "Reisepass"},
        basis="explicit",
        excerpt="Reisepass",
        extractor="llm",
        extractor_version="ext-1+clean-1+tax:abcd1234",
    )


def _mention() -> MentionItem:
    return MentionItem(
        catalogue_service_id=CATALOGUE_ID,
        title_i18n={"de": "Reisepass"},
        role="required",
        excerpt="Reisepass",
        source_field="llm",
        extractor="llm",
        extractor_version="ext-1",
    )


def test_post_edges_sends_the_batch_and_reads_the_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    """post_edges · the items reach the edges route and the response counts come back typed."""
    api = LlmApi([])
    client = api.client(monkeypatch)

    response = client.candidates.post_edges([_edge()])

    assert api.edge_posts[0][0]["basis"] == "explicit"
    assert (response.edges_created, response.edges_updated, response.edges_skipped, response.skipped) == (1, 0, 0, [])


def test_post_edges_raises_the_api_error_and_recognises_the_database_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """post_edges · a 507 database_soft_limit raises an error that says so; a 422 does not claim it."""
    api = LlmApi([])
    client = api.client(monkeypatch)
    api.edge_status, api.edge_detail = 507, '{"detail":"database_soft_limit"}'
    with pytest.raises(DiscoveryMachineApiError) as limit:
        client.candidates.post_edges([_edge()])
    api.edge_status, api.edge_detail = 422, "bad edge"
    with pytest.raises(DiscoveryMachineApiError) as invalid:
        client.candidates.post_edges([_edge()])

    assert limit.value.is_database_limit and not invalid.value.is_database_limit


def test_post_mentions_reads_the_unknown_code_count_and_defaults_it_to_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    """post_mentions · unknown_codes is carried from the response; an older API without it reads as 0."""
    api = LlmApi([])
    client = api.client(monkeypatch)
    api.unknown_codes = 2
    assert client.candidates.post_mentions([_mention()]).unknown_codes == 2

    assert (
        MentionsResponse.model_validate(
            {"candidates_created": 1, "mentions_created": 1, "mentions_updated": 0}
        ).unknown_codes
        == 0
    )
