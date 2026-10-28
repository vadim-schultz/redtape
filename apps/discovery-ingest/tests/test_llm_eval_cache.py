"""The eval result cache: a round trip, a miss for anything unknown, and a key that follows every input (chapter E5)."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from discovery_ingest.extract.llm.client import LlmResult
from discovery_ingest.extract.llm.evaluation.cache import CacheEntry, CacheKey, ResultCache, text_digest

KEY = CacheKey("@cf/m", "ext-1", "clean-1", "abcd1234", "alpha", text_digest("page text"))
ENTRY = CacheEntry(LlmResult('{"page_kind": "other"}', 1000, 200, "@cf/m"), 40.6)


def test_an_entry_comes_back_exactly_as_it_was_stored(tmp_path: Path) -> None:
    """ResultCache · put then get returns the answer, its token counts (also None) and its neurons."""
    cache = ResultCache(tmp_path / "nested" / "cache")
    unmetered = CacheEntry(LlmResult("{}", None, None, "@cf/m"), 12.0)

    cache.put(KEY, ENTRY)
    cache.put(replace(KEY, page="beta"), unmetered)

    assert cache.get(KEY) == ENTRY
    assert cache.get(replace(KEY, page="beta")) == unmetered


@pytest.mark.parametrize(
    "field", ["model", "prompt_version", "clean_version", "taxonomy_digest", "page", "text_digest"]
)
def test_the_key_follows_every_input_so_a_change_is_a_miss(tmp_path: Path, field: str) -> None:
    """CacheKey · changing the model, prompt version, cleaner version, vocabulary, page or text is a different entry."""
    cache = ResultCache(tmp_path)
    cache.put(KEY, ENTRY)

    assert cache.get(replace(KEY, **{field: "changed"})) is None
    assert cache.get(KEY) == ENTRY


def test_an_unknown_missing_or_damaged_entry_is_a_miss(tmp_path: Path) -> None:
    """ResultCache · no directory, a broken file and a file of the wrong shape all read as None."""
    assert ResultCache(tmp_path / "never-created").get(KEY) is None
    cache = ResultCache(tmp_path)
    cache.put(KEY, ENTRY)
    entry_file = tmp_path / KEY.filename()

    entry_file.write_text('{"result": {"parsed_json": 1}, "neurons": "x"}', encoding="utf-8")
    assert cache.get(KEY) is None
    entry_file.write_text("not json", encoding="utf-8")
    assert cache.get(KEY) is None
