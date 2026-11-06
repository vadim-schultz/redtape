"""PVOG payload harvester tests (chapter 7, loop A)."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import discovery_ingest
from discovery_ingest.harvest.pvog import EXTRACTOR, EXTRACTOR_VERSION, harvest_pvog_payload
from discovery_ingest.mentions import MentionDraft
from discovery_ingest.pvog.crosswalk_check import parse_crosswalk

from crosswalk_fakes import CROSSWALK, VOCABULARY

FIXTURES = Path(__file__).parent / "fixtures" / "pvog" / "details_modules.json"
MODULES: dict[str, dict[str, object]] = json.loads(FIXTURES.read_text(encoding="utf-8"))


def harvest(payload: dict[str, object]) -> list[MentionDraft]:
    """Harvest ``payload`` through the served crosswalk."""
    return harvest_pvog_payload(payload, CROSSWALK)


def _payload(*modules: dict[str, object], **extra: object) -> dict[str, object]:
    if (leaf_code := extra.get("_personal_matter_code")) is not None:
        extra["_pvog_source_path"] = {
            "root_code": "1",
            "root_label": "Lebenslagen für Bürgerinnen und Bürger",
            "parent_code": str(leaf_code)[:3],
            "leaf_code": leaf_code,
            "source_version": "v7",
        }
    return {"details": list(modules), **extra}


def _module(text: str, *, code: str = "08", filled: bool = True) -> dict[str, object]:
    return {"code": code, "title": "Modul", "text": text, "links": [], "filled": filled}


def _titles(payload: dict[str, object]) -> list[str]:
    return [draft.title_i18n["de"] for draft in harvest(payload)]


def test_harvester_extracts_one_required_mention_per_list_item_of_a_filled_documents_module() -> None:
    """harvester · extracts one required mention per list item of a filled documents module."""
    drafts = harvest(_payload(MODULES["lieferengpass"]))

    assert len(drafts) == 1
    assert drafts[0].title_i18n == {"de": "Lieferengpassmeldung"}
    assert drafts[0].role == "required"
    assert drafts[0].source_field == "details[code=08]"
    assert (drafts[0].extractor, drafts[0].extractor_version) == (EXTRACTOR, EXTRACTOR_VERSION)
    assert drafts[0].official_url is None
    assert "Lieferengpassmeldung" in drafts[0].excerpt


def test_harvester_takes_leaf_items_of_nested_lists_and_strips_trailing_connectives() -> None:
    """harvester · takes leaf items of nested lists and strips trailing connectives."""
    titles = _titles(_payload(MODULES["eid"]))

    assert titles == [
        "Personalausweis mit Online-Ausweisfunktion",
        "elektronischer Aufenthaltstitel",
        "eID-Karte für Bürgerinnen und Bürger der Europäischen Union und des Europäischen Wirtschaftsraums",
    ]
    assert "eID-Mittel zur Identifizierung" not in titles


def test_harvester_strips_bullets_and_numbering_and_falls_back_to_line_separated_paragraphs() -> None:
    """harvester · strips bullets and numbering and falls back to line separated paragraphs."""
    listed = _titles(_payload(_module("<ul><li>1. Personalausweis;</li><li>- Reisepass</li></ul>")))
    lines = _titles(_payload(_module("<p>Geburtsurkunde<br>Meldebescheinigung&#xa0;</p>")))

    assert listed == ["Personalausweis", "Reisepass"]
    assert lines == ["Geburtsurkunde", "Meldebescheinigung"]


def test_harvester_turns_form_links_into_form_mentions_with_the_link_uri_as_official_url() -> None:
    """harvester · turns form links into form mentions with the link uri as official url."""
    drafts = harvest(_payload(MODULES["formulare"]))

    assert [(d.title_i18n["de"], d.role, d.official_url, d.source_field) for d in drafts] == [
        ("Antrag auf Erlaubnis (PDF)", "form", "https://forms.example.de/antrag.pdf", "details[code=14]"),
        ("Anlage Sachkunde", "form", "https://forms.example.de/sachkunde.pdf", "details[code=14]"),
    ]


def test_harvester_skips_form_links_without_title_or_uri() -> None:
    """harvester · skips form links without title or uri."""
    links = [{"title": "", "uri": "https://x.example/a"}, {"title": "Ohne Uri"}, "not-a-link", {"uri": ""}]
    module = {**MODULES["formulare"], "links": links}

    assert harvest(_payload(module)) == []


def test_harvester_skips_unfilled_modules_and_placeholder_text() -> None:
    """harvester · skips unfilled modules and placeholder text."""
    unfilled = _module("<ul><li>Personalausweis</li></ul>", filled=False)
    placeholder = _module("<p>nicht angegeben</p>")
    unrelated = _module("<ul><li>Personalausweis</li></ul>", code="09")
    empty = _module("")

    assert harvest(_payload(unfilled, placeholder, unrelated, empty)) == []
    assert harvest({}) == []
    assert harvest({"details": "broken"}) == []


def test_harvester_drops_sentences_and_stop_list_items() -> None:
    """harvester · drops sentences and stop-list items."""
    assert harvest(_payload(MODULES["keine"])) == []

    stop_list = _module("<ul><li>keine</li><li>Siehe unten</li><li>ab</li><li>Reisepass</li></ul>")
    assert _titles(_payload(stop_list)) == ["Reisepass"]
    too_long = _module(f"<ul><li>{'Nachweis ' * 30}</li><li>Reisepass</li></ul>")
    assert _titles(_payload(too_long)) == ["Reisepass"]


def test_harvester_ignores_intro_paragraphs_when_the_module_has_list_items() -> None:
    """harvester · ignores intro paragraphs when the module has list items."""
    titles = _titles(_payload(MODULES["vorschlag"]))

    assert titles == [
        "Vorschlagsformular zur Einreichung der Vorschläge",
        "mit den zuständigen Fachverbänden abgestimmte Vorschläge mit deren schriftlichen Stellungnahmen",
    ]


def test_harvester_keeps_every_leaf_item_of_a_multi_list_module() -> None:
    """harvester · keeps every leaf item of a multi list module."""
    titles = _titles(_payload(MODULES["erlaubnis"]))

    assert "Nachweise über die erforderliche Sachkenntnis der Verantwortlichen" in titles
    assert "Straße und Hausnummer" in titles
    assert "Beschreibung der Lage der Betriebsstätten mit:" not in titles
    assert len(titles) == 6


def test_harvester_uses_the_payload_language_and_truncates_the_excerpt() -> None:
    """harvester · uses the payload language and truncates the excerpt."""
    long_text = "<ul><li>Reisepass</li></ul><p>" + "Hinweis " * 200 + "</p>"
    drafts = harvest(_payload(_module(long_text), languageCode="EN"))

    assert drafts[0].title_i18n == {"en": "Reisepass"}
    assert 0 < len(drafts[0].excerpt) <= 500


def test_harvester_is_deterministic() -> None:
    """harvester · is deterministic."""
    payload = _payload(MODULES["erlaubnis"], MODULES["formulare"], MODULES["eid"])

    assert harvest(payload) == harvest(payload)
    assert harvest(payload) == harvest(json.loads(json.dumps(payload)))


def test_harvester_reports_each_document_once_per_module() -> None:
    """harvester · reports each document once per module."""
    duplicated = _module("<ul><li>Reisepass</li><li>Reisepass</li></ul>")

    assert _titles(_payload(duplicated)) == ["Reisepass"]


def test_harvester_attaches_the_mapped_category_code_for_a_clean_leaf() -> None:
    """harvester · attaches the mapped single-element category code for a clean leaf."""
    drafts = harvest(_payload(MODULES["lieferengpass"], _personal_matter_code="1180100"))

    assert drafts[0].category_codes == ["retirement"]


def test_harvester_attaches_every_plausible_category_for_a_bundled_leaf() -> None:
    """harvester · attaches both plausible categories for a bundled/ambiguous leaf."""
    drafts = harvest(_payload(MODULES["lieferengpass"], _personal_matter_code="1040300"))

    assert drafts[0].category_codes == ["job-loss", "new-job"]


def test_harvester_attaches_nothing_when_the_stashed_code_is_unmapped() -> None:
    """harvester · attaches no category_codes for an unmapped leaf code."""
    drafts = harvest(_payload(MODULES["lieferengpass"], _personal_matter_code="1170100"))

    assert drafts[0].category_codes is None


def test_harvester_attaches_the_clean_leafs_mapping_clarity_confidence_and_leaf_code() -> None:
    """harvester · a clean leaf carries direct_category_confidence=0.95 and its own pvog_leaf_code."""
    drafts = harvest(_payload(MODULES["lieferengpass"], _personal_matter_code="1180100"))

    assert drafts[0].category_codes == ["retirement"]
    assert drafts[0].direct_category_confidence == 0.95
    assert drafts[0].pvog_leaf_code == "1180100"
    assert drafts[0].pvog_source_path is not None
    assert drafts[0].pvog_mapping_version == "category-contract-v1"


def test_harvester_attaches_0_65_confidence_on_both_categories_of_an_ambiguous_bundled_leaf() -> None:
    """harvester · an ambiguous bundled leaf carries 0.65 on both emitted category codes."""
    drafts = harvest(_payload(MODULES["lieferengpass"], _personal_matter_code="1040300"))

    assert drafts[0].category_codes == ["job-loss", "new-job"]
    assert drafts[0].direct_category_confidence == 0.65
    assert drafts[0].pvog_leaf_code == "1040300"


def test_harvester_attaches_the_canonical_category_for_a_former_domain_hint_leaf() -> None:
    """harvester · a formerly domain-only leaf carries canonical category evidence."""
    drafts = harvest(_payload(MODULES["lieferengpass"], _personal_matter_code="1020200"))

    assert drafts[0].category_codes == ["family-and-relationships"]
    assert drafts[0].direct_category_confidence == 0.8
    assert drafts[0].pvog_leaf_code == "1020200"


def test_harvester_attaches_no_category_for_a_source_only_leaf() -> None:
    """harvester · a source-only leaf carries no canonical category."""
    drafts = harvest(_payload(MODULES["lieferengpass"], _personal_matter_code="1170100"))

    assert drafts[0].category_codes is None
    assert drafts[0].direct_category_confidence is None
    assert drafts[0].pvog_leaf_code == "1170100"


def test_harvester_attaches_no_pvog_evidence_when_the_payload_has_none() -> None:
    """harvester · without a stashed leaf code, every PVOG field stays unset."""
    drafts = harvest(_payload(MODULES["lieferengpass"]))

    assert drafts[0].pvog_leaf_code is None
    assert drafts[0].direct_category_confidence is None
    assert drafts[0].category_codes is None


def test_harvest_maps_a_complete_pvog_path_through_the_crosswalk_it_is_given() -> None:
    """harvester · a fetched crosswalk, not any stored copy, decides the categories a complete path carries."""
    changed = copy.deepcopy(VOCABULARY)
    crosswalk = changed["crosswalk"]
    assert isinstance(crosswalk, dict)
    leaves = crosswalk["pvog_leaf_mappings"]
    assert isinstance(leaves, list)
    leaf = next(item for item in leaves if isinstance(item, dict) and item["leaf_code"] == "1050200")
    leaf.update(category_codes=["renting-home"], confidence=0.8)
    fetched = parse_crosswalk(changed)

    drafts = harvest_pvog_payload(_payload(MODULES["lieferengpass"], _personal_matter_code="1050200"), fetched)

    assert drafts[0].category_codes == ["renting-home"]
    assert drafts[0].direct_category_confidence == 0.8
    assert drafts[0].pvog_mapping_version == "category-contract-v1"


def test_no_ingest_module_names_the_contract_artifact_file() -> None:
    """ingest · no module under discovery_ingest names the contract artifact file, so ingest reads no repository file."""
    package = Path(discovery_ingest.__file__).parent
    markers = ("category-contract-v1.json", "category_contract_v1.json", "category-taxonomy-migration/category")
    offenders = [
        str(path.relative_to(package))
        for path in sorted(package.rglob("*.py"))
        if any(marker in path.read_text(encoding="utf-8") for marker in markers)
    ]

    assert offenders == []
