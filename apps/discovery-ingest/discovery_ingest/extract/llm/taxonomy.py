"""The closed category vocabulary as served by ``GET /machine/taxonomy``."""

from __future__ import annotations

import hashlib
import json

from pydantic import BaseModel, ConfigDict

DIGEST_LENGTH = 8


class TaxonomyTerm(BaseModel):
    """An active canonical category with every stored translation."""

    model_config = ConfigDict(frozen=True)

    code: str
    name_i18n: dict[str, str]
    description_i18n: dict[str, str]
    parent_code: str | None = None
    icon: str | None = None
    source_parent_codes: tuple[str, ...] = ()


class Taxonomy(BaseModel):
    """The active canonical categories in the order the API serves them; the endpoint serves only active ones."""

    model_config = ConfigDict(frozen=True)

    categories: tuple[TaxonomyTerm, ...]

    @property
    def category_codes(self) -> tuple[str, ...]:
        """Return category codes in served order."""
        return tuple(term.code for term in self.categories)

    @property
    def active_categories(self) -> tuple[TaxonomyTerm, ...]:
        """Return category terms in served order; every served term is active."""
        return self.categories

    def digest(self) -> str:
        """Return the first eight hex characters of the vocabulary SHA-256."""
        canonical = json.dumps(
            [term.model_dump(mode="json") for term in self.active_categories],
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:DIGEST_LENGTH]
