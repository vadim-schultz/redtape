"""The files of a locale: the seed JSON, its web mirror and the taxonomy module, written whole and read back (search-first C11)."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
from discovery_ingest.i18n.files import Layout, TranslationFiles, read_sources
from discovery_ingest.i18n.flat import dump_json, flatten, unflatten
from discovery_ingest.i18n.strings import taxonomy_key


def _layout(tmp_path: Path) -> Layout:
    return Layout(tmp_path / "seed", tmp_path / "web", tmp_path / "taxonomy_translations.py")


def test_flatten_and_unflatten_round_trip_dotted_keys_and_sort_them() -> None:
    """files · `a.b` nests under `a`; dumping sorts keys at every level and keeps non-ASCII text readable."""
    flat = {"b.y": "Ж", "a.x": "1", "b.x": "2"}

    assert flatten(unflatten(flat)) == flat
    assert dump_json(unflatten(flat)) == '{\n  "a": {\n    "x": "1"\n  },\n  "b": {\n    "x": "2",\n    "y": "Ж"\n  }\n}\n'


def test_a_key_that_is_both_a_value_and_a_branch_is_refused() -> None:
    """files · `a` and `a.b` cannot both exist in a nested file."""
    with pytest.raises(ValueError, match="a.b"):
        unflatten({"a": "x", "a.b": "y"})


def test_taxonomy_labels_are_written_as_a_python_module_and_read_back_with_other_locales_kept(tmp_path: Path) -> None:
    """files · the module maps code to locale to (name, description); writing one locale keeps the others."""
    files = TranslationFiles(_layout(tmp_path))
    files.write("tr", {taxonomy_key("housing", "name"): "Konut", taxonomy_key("housing", "description"): "Kira."})
    files.write("ru", {taxonomy_key("housing", "name"): "Жильё", taxonomy_key("housing", "description"): "Аренда."})

    module = ast.parse((tmp_path / "taxonomy_translations.py").read_text(encoding="utf-8"))
    assigned = next(node for node in module.body if isinstance(node, ast.AnnAssign))
    assert ast.literal_eval(assigned.value) == {"housing": {"ru": ("Жильё", "Аренда."), "tr": ("Konut", "Kira.")}}
    assert files.read("tr") == {taxonomy_key("housing", "name"): "Konut", taxonomy_key("housing", "description"): "Kira."}


def test_a_label_with_only_a_name_is_not_written_half_finished(tmp_path: Path) -> None:
    """files · a category needs its name and its description; a lone name stays out of the module."""
    files = TranslationFiles(_layout(tmp_path))

    files.write("tr", {taxonomy_key("housing", "name"): "Konut"})

    assert files.read("tr") == {}


def test_reading_a_locale_without_files_is_empty(tmp_path: Path) -> None:
    """files · no seed file and no module yet means nothing is translated."""
    assert TranslationFiles(_layout(tmp_path)).read("pl") == {}


def test_the_sources_are_the_english_and_german_files_plus_the_active_categories(tmp_path: Path) -> None:
    """files · read_sources pairs en and de per key and adds a name and a description per active category."""
    layout = _layout(tmp_path)
    layout.seed_dir.mkdir()
    (layout.seed_dir / "en.json").write_text(json.dumps({"a": {"b": "Hi {n}"}}), encoding="utf-8")
    (layout.seed_dir / "de.json").write_text(json.dumps({"a": {"b": "Hallo {n}"}}), encoding="utf-8")
    contract = tmp_path / "contract.json"
    contract.write_text(
        json.dumps(
            {
                "categories": [
                    {"code": "housing", "is_active": True, "name_i18n": {"de": "Wohnen", "en": "Housing"},
                     "description_i18n": {"de": "Mieten.", "en": "Renting."}},
                    {"code": "old", "is_active": False, "name_i18n": {"de": "Alt", "en": "Old"},
                     "description_i18n": {"de": "Alt.", "en": "Old."}},
                ]
            }
        ),
        encoding="utf-8",
    )

    sources = read_sources(layout, contract)

    assert [(s.key, s.german, s.english) for s in sources] == [
        ("a.b", "Hallo {n}", "Hi {n}"),
        (taxonomy_key("housing", "name"), "Wohnen", "Housing"),
        (taxonomy_key("housing", "description"), "Mieten.", "Renting."),
    ]


def test_english_and_german_files_with_different_keys_are_refused(tmp_path: Path) -> None:
    """files · a key only one of the two sources has is a stop, not a guess."""
    layout = _layout(tmp_path)
    layout.seed_dir.mkdir()
    (layout.seed_dir / "en.json").write_text(json.dumps({"a": "x", "b": "y"}), encoding="utf-8")
    (layout.seed_dir / "de.json").write_text(json.dumps({"a": "x"}), encoding="utf-8")
    contract = tmp_path / "contract.json"
    contract.write_text(json.dumps({"categories": []}), encoding="utf-8")

    with pytest.raises(ValueError, match="b"):
        read_sources(layout, contract)
