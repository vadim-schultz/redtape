"""Category codes only · mention, curation and gold inputs refuse the retired axis fields by name (chapter C7).

The retired ``domain_codes``, ``situation_codes`` and their ``direct_*`` confidences are no longer translated. A payload
that still carries one is refused, and the error names the field. The removed PVOG modules no longer import.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
from discovery_ingest.curation import CurationFile
from discovery_ingest.extract.llm.evaluation.gold import GoldPage
from discovery_ingest.extract.llm.taxonomy import Taxonomy
from discovery_ingest.mentions import MentionItem
from pydantic import ValidationError

GOLD_DIR = Path(__file__).parent / "fixtures" / "gold"
RETIRED_VALUES: dict[str, object] = {
    "domain_codes": ["identity-civil-status"],
    "situation_codes": ["moving-house"],
    "direct_domain_confidence": 0.4,
    "direct_situation_confidence": 0.7,
}
LEGACY_LABEL_FIELDS = ("domain_codes", "situation_codes")
REMOVED_MODULES = ("discovery_ingest.pvog.domain_mapping", "discovery_ingest.pvog.situation_mapping")
PINNED_TAXONOMY_DIGEST = "c45150c7"
PINNED_GOLD_LINKS: dict[str, list[str]] = {
    "aa-arbeitslos-schritte": ["work-and-employment", "job-loss"],
    "aa-ferienbeschaeftigung": ["work-and-employment"],
    "aa-probebeschaeftigung": ["work-and-employment", "new-job"],
    "aa-transferkurzarbeitergeld": ["work-and-employment", "job-loss"],
    "auswaertiges-amt-start": [],
    "bfj-gewerbezentralregister": ["law-and-justice", "work-and-employment"],
    "ble-fleisch-intervention": [],
    "ble-kaese-lagerhaltung": [],
    "ble-wein-neuanpflanzung": ["work-and-employment"],
    "bundesarchiv-akteneinsicht": ["law-and-justice"],
    "bvl-tierarzneimittel-meldung": [],
    "bzkj-antrag-indizierung": ["law-and-justice"],
    "fragebogen-bundeskartellamt-registrierung": [],
    "goaml-start": [],
    "kba-zfer-login": [],
    "nebenwirkungen-melden": ["health-and-care"],
    "netzausbau-start": [],
    "verwaltung-fluggastrechte-anzeige": [],
    "verwaltung-js-shell": [],
    "vorsorgeregister-registrierung": ["law-and-justice", "illness-and-care"],
}

MENTION: dict[str, object] = {
    "catalogue_service_id": "00000000-0000-0000-0000-000000000001",
    "title_i18n": {"de": "Antrag"},
    "role": "required",
    "excerpt": "Ein Antrag ist erforderlich.",
    "source_field": "documents",
    "extractor": "llm",
    "extractor_version": "1",
}


def _candidate(**fields: object) -> dict[str, object]:
    """Return one curation candidate with a tag note; ``fields`` add its tag fields."""
    return {
        "candidate_id": "00000000-0000-0000-0000-000000000002",
        "catalogue_service_id": "00000000-0000-0000-0000-000000000003",
        "title_de": "Meldebescheinigung",
        "tag_note": "issued when moving",
        "requires": [],
        "required_by": [],
        **fields,
    }


def _curation_file(*candidates: dict[str, object]) -> dict[str, object]:
    """Return a curation file holding ``candidates``."""
    return {"version": 1, "curator": "test", "candidates": list(candidates)}


def _gold(**fields: object) -> dict[str, object]:
    """Return a gold page with no labels; ``fields`` add its label fields."""
    return {
        "name": "antrag",
        "html": "<html></html>",
        "source_url": "https://portal.example/antrag",
        "page_kind": "service",
        "documents": [],
        "dependencies": [],
        **fields,
    }


def _committed_labels() -> dict[str, dict[str, object]]:
    """Return every committed gold label by page name."""
    return {
        path.name.removesuffix(".gold.json"): json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(GOLD_DIR.glob("*.gold.json"))
    }


@pytest.mark.parametrize(("field", "value"), RETIRED_VALUES.items())
def test_mention_refuses_a_retired_axis_field_by_name(field: str, value: object) -> None:
    """Mention · a payload that still carries a retired axis field is refused, and the error names the field."""
    with pytest.raises(ValidationError, match=field):
        MentionItem.model_validate({**MENTION, field: value})


@pytest.mark.parametrize(("field", "value"), RETIRED_VALUES.items())
def test_curation_refuses_a_retired_axis_field_by_name(field: str, value: object) -> None:
    """Curation · a candidate that still carries a retired axis field is refused, and the error names the field."""
    with pytest.raises(ValidationError, match=field):
        CurationFile.model_validate(_curation_file(_candidate(**{field: value})))


@pytest.mark.parametrize("field", LEGACY_LABEL_FIELDS)
def test_gold_label_refuses_a_retired_axis_field_by_name(field: str) -> None:
    """Gold · a label that still carries a retired axis field is refused, and the error names the field."""
    with pytest.raises(ValidationError, match=field):
        GoldPage.model_validate(_gold(**{field: ["housing"]}))


@pytest.mark.parametrize("module", REMOVED_MODULES)
def test_removed_legacy_pvog_module_no_longer_imports(module: str) -> None:
    """Removed modules · the legacy domain and situation tables are gone, so nothing can import them."""
    assert importlib.util.find_spec(module) is None


def test_mention_keeps_category_codes_as_given() -> None:
    """Mention · category codes and the direct confidence are accepted as given, with no legacy field."""
    item = MentionItem.model_validate(
        {**MENTION, "category_codes": ["home-and-housing", "moving-house"], "direct_category_confidence": 0.8}
    )

    assert item.category_codes == ["home-and-housing", "moving-house"]
    assert item.direct_category_confidence == 0.8


def test_curation_keeps_category_codes_as_given() -> None:
    """Curation · category codes are accepted as given on each candidate, with no legacy field."""
    file = CurationFile.model_validate(
        _curation_file(_candidate(category_codes=["identity-and-documents", "moving-house"]))
    )

    assert file.candidates[0].category_codes == ["identity-and-documents", "moving-house"]


def test_gold_label_keeps_category_codes_as_given() -> None:
    """Gold · a label with category codes validates as given, with no legacy field."""
    page = GoldPage.model_validate(_gold(category_codes=["retirement"]))

    assert page.category_codes == ("retirement",)


def test_committed_gold_labels_carry_no_legacy_field() -> None:
    """Gold fixtures · no committed label names a retired domain or situation field."""
    for name, labels in _committed_labels().items():
        assert not set(LEGACY_LABEL_FIELDS) & labels.keys(), name


def test_committed_gold_labels_keep_the_category_links_they_had() -> None:
    """Gold fixtures · each page keeps the category links its legacy labels translated to before C7."""
    assert {name: labels["category_codes"] for name, labels in _committed_labels().items()} == PINNED_GOLD_LINKS


def test_committed_gold_taxonomy_is_the_served_shape_with_its_vocabulary() -> None:
    """Gold taxonomy · the fixture uses the served ``categories`` shape and keeps the vocabulary it had."""
    raw = json.loads((GOLD_DIR / "taxonomy.json").read_text(encoding="utf-8"))

    assert set(raw) == {"categories"}
    assert Taxonomy.model_validate(raw).digest() == PINNED_TAXONOMY_DIGEST
