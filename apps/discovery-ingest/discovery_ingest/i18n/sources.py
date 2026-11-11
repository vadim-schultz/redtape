"""Read the strings to translate: the English and German seed files and the active categories from the machine API."""

from __future__ import annotations

from collections.abc import Iterator

from discovery_ingest.extract.llm.taxonomy import Taxonomy, TaxonomyTerm
from discovery_ingest.i18n.files import Layout, read_flat
from discovery_ingest.i18n.strings import SourceString, category_strings, ui_strings


def _texts(term: TaxonomyTerm, locale: str) -> dict[str, str]:
    """Return the name and description of ``term`` in ``locale``; a category without either raises :class:`ValueError`."""
    try:
        return {"name": term.name_i18n[locale], "description": term.description_i18n[locale]}
    except KeyError:
        raise ValueError(f"category {term.code!r} has no {locale} name or description") from None


def _category_strings(taxonomy: Taxonomy) -> Iterator[SourceString]:
    for term in taxonomy.active_categories:
        yield from category_strings(term.code, _texts(term, "en"), _texts(term, "de"))


def read_sources(layout: Layout, taxonomy: Taxonomy) -> list[SourceString]:
    """Return every string to translate: the interface keys, then a name and a description per active category."""
    english, german = read_flat(layout.seed_dir / "en.json"), read_flat(layout.seed_dir / "de.json")
    return [*ui_strings(english, german), *_category_strings(taxonomy)]
