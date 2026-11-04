"""A four-term vocabulary for the probe, which has no access to the Discovery API and so cannot fetch the real one."""

from __future__ import annotations

from discovery_ingest.extract.llm.taxonomy import Taxonomy, TaxonomyTerm


def _term(code: str, name_de: str, name_en: str) -> TaxonomyTerm:
    return TaxonomyTerm(code=code, name_i18n={"de": name_de, "en": name_en}, description_i18n={})


PROBE_TAXONOMY = Taxonomy(
    categories=(
        _term("home-and-housing", "Wohnen", "Home and housing"),
        _term("moving-house", "Umzug", "Moving house"),
        _term("identity-and-documents", "Identität", "Identity and documents"),
        _term("birth-and-parenthood", "Geburt", "Birth of a child"),
    ),
)
