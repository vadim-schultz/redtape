"""Pure comparison helper behind DocumentPromotion.find_conflicts; no database session needed."""

from __future__ import annotations

import uuid

from app.features.documents.promotion import _conflicting_document_ids


def test_matches_on_slug() -> None:
    doc_id = uuid.uuid4()
    rows = [(doc_id, "residency-permit", "https://example.gov/other")]

    assert _conflicting_document_ids(rows, slug="residency-permit", normalized_url="https://example.gov/x") == [doc_id]


def test_matches_on_normalized_url() -> None:
    doc_id = uuid.uuid4()
    rows = [(doc_id, "other-slug", "https://Example.gov/residency/")]

    assert _conflicting_document_ids(rows, slug="unrelated-slug", normalized_url="https://example.gov/residency") == [
        doc_id
    ]


def test_ignores_rows_with_no_official_url() -> None:
    rows = [(uuid.uuid4(), "other-slug", None)]

    assert _conflicting_document_ids(rows, slug="unrelated-slug", normalized_url="https://example.gov/residency") == []


def test_no_match_returns_an_empty_list() -> None:
    rows = [(uuid.uuid4(), "other-slug", "https://example.gov/other")]

    assert _conflicting_document_ids(rows, slug="unrelated-slug", normalized_url="https://example.gov/residency") == []


def test_without_a_url_only_the_slug_can_match() -> None:
    same_slug, other = uuid.uuid4(), uuid.uuid4()
    rows = [(same_slug, "residency-permit", None), (other, "other-slug", "https://example.gov/residency")]

    assert _conflicting_document_ids(rows, slug="residency-permit", normalized_url=None) == [same_slug]


def test_without_a_url_or_a_matching_slug_nothing_matches() -> None:
    rows = [(uuid.uuid4(), "other-slug", "https://example.gov/residency"), (uuid.uuid4(), "third", None)]

    assert _conflicting_document_ids(rows, slug="residency-permit", normalized_url=None) == []
