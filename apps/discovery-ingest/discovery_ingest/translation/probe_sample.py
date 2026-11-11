"""The probe's input: the public candidate list as translation units, and a fixed reproducible sample of it."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Final

import httpx
from pydantic import BaseModel, ValidationError

from discovery_ingest.translation.units import TranslationUnit

SAMPLE_SEED: Final = 13
"""The probe always draws with this seed, so two runs (and two engines) see the same candidates."""
PAGE_LIMIT: Final = 100
MAX_PAGES: Final = 200
CANDIDATES_PATH: Final = "/api/v1/candidates/"


class ProbeSourceError(Exception):
    """The candidate list could not be read; the probe has nothing to translate."""


@dataclass(frozen=True, slots=True)
class Corpus:
    """Every card of the public list as a unit, and the ``total`` the API reports (the corpus size to project onto)."""

    units: tuple[TranslationUnit, ...]
    total: int


class Card(BaseModel):
    """The two fields of a public candidate card that are translated."""

    id: str
    title: str
    description: str | None = None

    def to_unit(self) -> TranslationUnit:
        """Return the card as a unit; a card without a description has an empty one."""
        return TranslationUnit(self.id, self.title, self.description or "")


class CardPage(BaseModel):
    """One page of ``GET /api/v1/candidates/``."""

    items: list[Card]
    total: int


class PublicCandidateReader:
    """Read the whole public candidate list in German, page by page; it is public, so no credential is involved."""

    def __init__(self, base_url: str, http: httpx.Client) -> None:
        """Keep the API base URL and the HTTP client."""
        self._base_url = base_url.rstrip("/")
        self._http = http

    def read(self) -> Corpus:
        """Return every card as a unit and the reported total; raise :class:`ProbeSourceError` on any failure."""
        units: list[TranslationUnit] = []
        total = 0
        for page_number in range(MAX_PAGES):
            page = self._page(page_number * PAGE_LIMIT)
            total = page.total
            units.extend(card.to_unit() for card in page.items)
            if len(page.items) < PAGE_LIMIT or len(units) >= total:
                break
        return Corpus(tuple(units), total)

    def _page(self, offset: int) -> CardPage:
        params: dict[str, str | int] = {"locale": "de", "limit": PAGE_LIMIT, "offset": offset}
        try:
            response = self._http.get(f"{self._base_url}{CANDIDATES_PATH}", params=params)
            if response.status_code >= 400:
                raise ProbeSourceError(f"the candidate list answered HTTP {response.status_code}")
            return CardPage.model_validate(response.json())
        except (httpx.HTTPError, ValidationError, ValueError) as err:
            raise ProbeSourceError(f"the candidate list could not be read: {type(err).__name__}") from err


def pick_sample(units: tuple[TranslationUnit, ...], count: int) -> tuple[TranslationUnit, ...]:
    """Return ``count`` units drawn with the fixed seed from the units sorted by key, so the order of ``units`` is irrelevant."""
    ordered = sorted(units, key=lambda unit: unit.key)
    chosen = random.Random(SAMPLE_SEED).sample(ordered, min(count, len(ordered)))
    return tuple(sorted(chosen, key=lambda unit: unit.key))
