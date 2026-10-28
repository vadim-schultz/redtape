"""A small on-disk cache of model answers, so an unchanged page costs nothing on a re-run."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from pydantic import ValidationError

from discovery_ingest.extract.llm.client import LlmResult


@dataclass(frozen=True, slots=True)
class CacheKey:
    """What an answer depends on: the model, the prompt, the cleaner, the vocabulary and the page text."""

    model: str
    prompt_version: str
    clean_version: str
    taxonomy_digest: str
    page: str
    text_digest: str

    def filename(self) -> str:
        """Return the file name of this key: a digest of every field, so any change is a new entry."""
        canonical = json.dumps(asdict(self), sort_keys=True)
        return f"{hashlib.sha256(canonical.encode()).hexdigest()}.json"


@dataclass(frozen=True, slots=True)
class CacheEntry:
    """A cached answer with the neurons it cost when it was paid for."""

    result: LlmResult
    neurons: float


def text_digest(text: str) -> str:
    """Return a short digest of the cleaned page text."""
    return hashlib.sha256(text.encode()).hexdigest()[:16]


class ResultCache:
    """Read and write :class:`CacheEntry` files in one directory; an unreadable file is a miss."""

    def __init__(self, directory: Path) -> None:
        """Keep answers under ``directory``, created on the first write."""
        self._directory = directory

    def get(self, key: CacheKey) -> CacheEntry | None:
        """Return the entry for ``key``, or ``None`` when it was never stored or cannot be read."""
        path = self._directory / key.filename()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return CacheEntry(LlmResult(**data["result"]), float(data["neurons"]))
        except (OSError, ValueError, KeyError, TypeError, ValidationError):
            return None

    def put(self, key: CacheKey, entry: CacheEntry) -> None:
        """Store ``entry`` under ``key``."""
        self._directory.mkdir(parents=True, exist_ok=True)
        payload = {"result": asdict(entry.result), "neurons": entry.neurons}
        (self._directory / key.filename()).write_text(json.dumps(payload), encoding="utf-8")
