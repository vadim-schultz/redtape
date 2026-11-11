"""Content hash of a search text (chapter 4)."""

from __future__ import annotations

import hashlib

import app.features.search.hashing as hashing
import pytest
from app.features.search.hashing import RECIPE_VERSION, content_hash


def test_hash_is_sha256_of_recipe_version_newline_text() -> None:
    expected = hashlib.sha256(f"{RECIPE_VERSION}\nKindergeld".encode()).hexdigest()

    assert content_hash("Kindergeld") == expected
    assert content_hash("Kindergeld") == content_hash("Kindergeld")


def test_different_text_gives_a_different_hash() -> None:
    assert content_hash("Kindergeld") != content_hash("Elterngeld")


def test_a_recipe_version_bump_changes_every_hash(monkeypatch: pytest.MonkeyPatch) -> None:
    before = {text: content_hash(text) for text in ("Kindergeld", "Elterngeld", "")}

    monkeypatch.setattr(hashing, "RECIPE_VERSION", "v2")

    assert all(content_hash(text) != digest for text, digest in before.items())
