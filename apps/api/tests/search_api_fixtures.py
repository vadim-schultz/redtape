"""Fixtures of the search API tests: a client with hybrid search on and a scripted query embedder."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from app.config import settings
from app.main import create_app
from app.models.discovery import DiscoveryDocumentCandidate
from litestar import Litestar
from litestar.testing import TestClient
from scripts.seed_taxonomy import seed_canonical_taxonomy
from sqlalchemy.orm import Session

from candidates_public_world import Scene
from query_embedder_support import FakeQueryEmbedder
from search_query_world import add_embedding, at_similarity, query_vector
from search_support import search_service

URL = "/api/v1/candidates"


@pytest.fixture
def embedder() -> FakeQueryEmbedder:
    """An embedder that gives every query below the same vector, ``query_vector()``."""
    return FakeQueryEmbedder()


def serve_with(
    monkeypatch: pytest.MonkeyPatch, db_session: Session, embedder: object, *, hybrid: bool = True
) -> TestClient[Litestar]:
    """Return a client of a fresh app whose candidate service uses ``embedder`` and the test session."""
    seed_canonical_taxonomy(db_session)
    monkeypatch.setattr("app.main.provide_session", lambda: db_session)
    monkeypatch.setattr("app.features.search.dependencies.get_query_embedder", lambda: embedder)
    monkeypatch.setattr(settings, "search_hybrid_enabled", hybrid)
    return TestClient(create_app())


@pytest.fixture
def search_client(
    db_session: Session, monkeypatch: pytest.MonkeyPatch, embedder: FakeQueryEmbedder
) -> Iterator[TestClient[Litestar]]:
    """A client with hybrid search on."""
    with serve_with(monkeypatch, db_session, embedder) as test_client:
        yield test_client


@pytest.fixture
def search_scene(db_session: Session) -> Scene:
    """The rows of one test."""
    return Scene(db_session)


def vector_for(*texts: str) -> dict[str, tuple[float, ...]]:
    """Return the scripted vectors that map every one of ``texts`` to the query vector."""
    return {text: query_vector() for text in texts}


def keys(response) -> list[str]:  # noqa: ANN001
    """Return the candidate keys of a list response in order."""
    return [item["key"] for item in response.json()["items"]]


def indexed_scored(
    session: Session,
    search_scene: Scene,
    key: str,
    title: str,
    categories: dict[str, float],
    *,
    similarity: float | None,
) -> DiscoveryDocumentCandidate:
    """Add a categorised candidate with a search text and, when ``similarity`` is given, an embedding."""
    candidate = search_scene.scored(key, categories=categories, title={"de": title})
    search_service(session).refresh(candidate.id)
    if similarity is not None:
        add_embedding(session, candidate, at_similarity(similarity))
    return candidate
