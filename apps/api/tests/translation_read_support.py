"""Builders for the translation read tests: a client with enabled locales and a counting store, and stored cards."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import app.features.discovery.dependencies as discovery_dependencies
import pytest
from app.main import create_app
from app.models.discovery import DiscoveryDocumentCandidate
from app.shared.object_store import InMemoryObjectStore, MeteredObjectStore, ObjectStore, ObjectStoreMeter, noop_meter
from litestar import Litestar
from litestar.testing import TestClient
from scripts.seed_taxonomy import seed_canonical_taxonomy
from sqlalchemy import event
from sqlalchemy.orm import Session

from candidates_public_world import Scene
from search_locale_support import payload, store_translation

URL = "/api/v1/candidates"
LOCALES = {"de", "en", "tr"}


class CountingStore(InMemoryObjectStore):
    """An in-memory store that counts the reads that reach it."""

    def __init__(self) -> None:
        super().__init__()
        self.reads = 0

    def get(self, key: str) -> bytes:
        self.reads += 1
        return super().get(key)


class StoreSlot:
    """The store the app resolves for its ``object_store`` dependency; a test may clear it to model no storage."""

    def __init__(self) -> None:
        self.memory = CountingStore()
        self.store: ObjectStore | None = self.memory


@pytest.fixture
def slot(monkeypatch: pytest.MonkeyPatch) -> StoreSlot:
    """Put the slot's store under the ledger meter the candidate routes pass to ``get_object_store``."""
    holder = StoreSlot()

    def metered_slot_store(meter: ObjectStoreMeter = noop_meter) -> ObjectStore | None:
        return None if holder.store is None else MeteredObjectStore(holder.store, meter)

    monkeypatch.setattr(discovery_dependencies, "get_object_store", metered_slot_store)
    return holder


@pytest.fixture
def reader(
    db_session: Session, monkeypatch: pytest.MonkeyPatch, slot: StoreSlot
) -> Iterator[TestClient[Litestar]]:
    """A client of the public candidate routes that serves ``de``, ``en`` and ``tr`` and reads from ``slot``."""
    seed_canonical_taxonomy(db_session)
    monkeypatch.setattr("app.main.provide_session", lambda: db_session)
    monkeypatch.setattr("app.lifespan._load_enabled_locales", lambda: set(LOCALES))
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def scene(db_session: Session) -> Scene:
    """The rows of one test."""
    return Scene(db_session)


def translated(
    scene: Scene,
    slot: StoreSlot,
    key: str = "kindergeld",
    *,
    title: str = "Kindergeldantrag",
    excerpt: str = "Bitte Ausweis mitbringen",
    locale: str = "tr",
    translated_title: str = "Çocuk parası başvurusu",
    translated_description: str = "Kimlik getirin",
) -> DiscoveryDocumentCandidate:
    """Add a candidate with one mention and a stored translation into ``locale`` that matches its German unit."""
    owner = scene.candidate(key, title={"de": title})
    scene.mention(owner, scene.procedure(), excerpt=excerpt)
    translation = payload(locale, translated_title, translated_description)
    store_translation(scene.session, slot.memory, owner, translation)
    return owner


@contextmanager
def count_queries(session: Session) -> Iterator[list[str]]:
    """Collect the SQL statements the session's connection executes inside the block."""
    statements: list[str] = []
    connection = session.connection()

    def _record(_conn: object, _cursor: object, statement: str, *_rest: object) -> None:
        statements.append(statement)

    event.listen(connection, "before_cursor_execute", _record)
    try:
        yield statements
    finally:
        event.remove(connection, "before_cursor_execute", _record)
