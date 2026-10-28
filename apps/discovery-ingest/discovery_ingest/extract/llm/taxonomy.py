"""The closed tag vocabulary as served by ``GET /machine/taxonomy``."""

from __future__ import annotations

import hashlib
import json

from pydantic import BaseModel, ConfigDict

DIGEST_LENGTH = 8


class TaxonomyTerm(BaseModel):
    """A domain or life situation with every stored translation."""

    model_config = ConfigDict(frozen=True)

    code: str
    name_i18n: dict[str, str]
    description_i18n: dict[str, str]


class Taxonomy(BaseModel):
    """Both closed vocabularies in the order the API serves them."""

    model_config = ConfigDict(frozen=True)

    domains: tuple[TaxonomyTerm, ...]
    situations: tuple[TaxonomyTerm, ...]

    @property
    def domain_codes(self) -> tuple[str, ...]:
        """The domain codes in served order."""
        return tuple(term.code for term in self.domains)

    @property
    def situation_codes(self) -> tuple[str, ...]:
        """The life-situation codes in served order."""
        return tuple(term.code for term in self.situations)

    def digest(self) -> str:
        """Return the first eight hex characters of the SHA-256 of the vocabulary the model is shown."""
        canonical = json.dumps(self.model_dump(mode="json"), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:DIGEST_LENGTH]
