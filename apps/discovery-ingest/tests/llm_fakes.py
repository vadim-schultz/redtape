"""Canned vocabulary and cleaned pages shared by the extraction schema, prompt, grounding and mapping tests."""

from __future__ import annotations

from discovery_ingest.extract.clean import CLEAN_VERSION, CleanPage
from discovery_ingest.extract.llm.taxonomy import Taxonomy, TaxonomyTerm

PAGE_URL = "https://portal.example/dienst/"


def term(code: str, name_de: str, name_en: str, description: str = "") -> TaxonomyTerm:
    """Build one vocabulary term with German and English names."""
    return TaxonomyTerm(
        code=code,
        name_i18n={"de": name_de, "en": name_en},
        description_i18n={"en": description} if description else {},
    )


def taxonomy() -> Taxonomy:
    """A two-by-two vocabulary shaped like ``GET /machine/taxonomy``."""
    return Taxonomy(
        domains=(
            term("housing", "Wohnen", "Housing", "Rent, registration and home ownership"),
            term("identity-civil-status", "Identität", "Identity", "Identity papers"),
        ),
        situations=(
            term("moving-house", "Umzug", "Moving house", "Changing the home address"),
            term("birth-of-child", "Geburt", "Birth of a child"),
        ),
    )


def page(text: str, *, links: tuple[str, ...] = (), language: str | None = "de") -> CleanPage:
    """A cleaned page with the given text and link set."""
    return CleanPage(text, frozenset(links), language, None, False, CLEAN_VERSION)
