"""Translation-memory probe · the block identity, the locale share, the memory hit rate and the export reader."""

import json
from pathlib import Path

import pytest

import translation_memory_probe as probe


def _record(locale, *blocks, page="p"):
    return probe.Record(locale, page, tuple(blocks))


def test_the_same_text_hashes_alike_after_whitespace_and_unicode_normalisation():
    """Probe · a block's identity ignores runs of whitespace and the decomposed or composed form of a letter."""
    assert probe.block_hash("Reisepass  beantragen") == probe.block_hash("Reisepass beantragen ")
    assert probe.block_hash("Gebühren") == probe.block_hash("Gebühren")


def test_different_texts_hash_apart():
    """Probe · two different sentences never share an identity."""
    assert probe.block_hash("Erwachsene: 60 Euro") != probe.block_hash("Kinder: 37,50 Euro")


def test_a_block_present_in_two_locales_is_shared_and_one_present_in_one_is_not():
    """Probe · of two distinct texts, the one in two locales is the shared share: one half."""
    measured = probe.measure([_record("en", "A", "B"), _record("tr", "A")])

    assert (measured.distinct_block_hashes, measured.shared_across_locales) == (2, 0.5)


def test_a_repeat_of_a_block_in_the_same_locale_is_a_memory_hit():
    """Probe · a second occurrence of a text in the same locale is a hit: one of the three occurrences."""
    measured = probe.measure([_record("en", "A"), _record("en", "A", "C")])

    assert (measured.occurrences, measured.memory_hit_rate) == (3, round(1 / 3, 4))


def test_the_same_text_in_another_locale_is_not_a_memory_hit():
    """Probe · a text in a second locale needs its own translation, so it is no hit for a table keyed by locale."""
    measured = probe.measure([_record("en", "A"), _record("tr", "A")])

    assert (measured.memory_hit_rate, measured.shared_across_locales) == (0.0, 1.0)


def test_an_empty_export_measures_zero_everywhere_without_dividing_by_zero():
    """Probe · an export with no blocks reports zeros; nothing divides by zero."""
    measured = probe.measure([])

    assert (measured.pages, measured.occurrences, measured.distinct_block_hashes) == (0, 0, 0)
    assert (measured.shared_across_locales, measured.memory_hit_rate) == (0.0, 0.0)


def test_a_line_that_is_not_a_stored_snapshot_translation_names_its_line_number():
    """Probe · a malformed line stops the read with its line number; blank lines are skipped."""
    lines = [json.dumps({"locale": "en", "page": "p", "blocks": ["A"]}), "", '{"locale": "en"}']

    with pytest.raises(ValueError, match="line 3"):
        probe.read_records(lines)


def test_the_main_reads_the_export_and_prints_the_measurement_as_json(tmp_path: Path, capsys):
    """Probe · the command reads a JSON-lines export and prints the measurement, and exits 0."""
    export = tmp_path / "export.jsonl"
    export.write_text(
        json.dumps({"locale": "en", "page": "1", "blocks": ["A", "B"]})
        + "\n"
        + json.dumps({"locale": "tr", "page": "2", "blocks": ["A"]})
        + "\n",
        encoding="utf-8",
    )

    assert probe.main([str(export)]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert (printed["pages"], printed["locales"], printed["distinct_block_hashes"]) == (2, ["en", "tr"], 2)
    assert printed["shared_across_locales"] == 0.5


def test_the_main_refuses_a_malformed_export_with_exit_code_two(tmp_path: Path, capsys):
    """Probe · a malformed export exits 2 and names the line, and prints no measurement."""
    export = tmp_path / "bad.jsonl"
    export.write_text("not json\n", encoding="utf-8")

    assert probe.main([str(export)]) == 2
    assert "line 1" in capsys.readouterr().err
