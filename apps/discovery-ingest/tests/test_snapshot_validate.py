"""Validation of translated blocks: a structural mismatch fails the page, one failing block keeps its German text."""

from __future__ import annotations

from discovery_ingest.snapshot_translation.blocks import Block
from discovery_ingest.snapshot_translation.validate_blocks import CheckedBlock, Rejected, check_page

GERMAN = "Bitte bringen Sie die Unterlagen mit."
URLS = ("(https://a.de)",)


def _p(text: str) -> Block:
    return Block("p", (text,))


def test_a_translation_that_keeps_every_promise_is_kept() -> None:
    checked = check_page((_p(GERMAN),), (_p("Please bring the documents."),), ())
    assert checked == (CheckedBlock(_p("Please bring the documents."), None),)


def test_a_block_count_mismatch_fails_the_whole_page() -> None:
    source = (_p("Erster Satz."), _p("Zweiter Satz."), _p("Dritter Satz."))
    translated = (_p("First sentence."), _p("Second sentence."))
    assert isinstance(check_page(source, translated, ()), Rejected)


def test_a_kind_mismatch_fails_the_whole_page() -> None:
    source = (Block("h2", ("Titel",)), _p("Text im Absatz."))
    translated = (_p("Title"), Block("h2", ("Paragraph text.",)))
    assert isinstance(check_page(source, translated, ()), Rejected)


def test_one_failing_block_is_returned_as_untranslated_and_the_others_are_kept() -> None:
    source = (_p("Erster Satz mit Inhalt."), _p("Zweiter Satz mit Inhalt."), _p("Dritter Satz mit Inhalt."))
    translated = (_p("First sentence with content."), _p(""), _p("Third sentence with content."))
    checked = check_page(source, translated, ())
    assert isinstance(checked, tuple)
    assert [item.untranslated for item in checked] == [False, True, False]
    assert checked[1].block == source[1]
    assert checked[0].block == translated[0]


def test_a_lost_token_fails_that_block_and_keeps_the_german_with_its_link() -> None:
    source = (Block("p", ("Antrag ⟦0⟧ bitte",)),)
    checked = check_page(source, (_p("Application please"),), URLS)
    assert isinstance(checked, tuple)
    assert checked[0].untranslated
    assert "token" in (checked[0].problem or "")
    assert checked[0].block == Block("p", ("Antrag (https://a.de) bitte",))


def test_an_invented_token_fails_that_block() -> None:
    checked = check_page((_p("Antrag bitte."),), (_p("Application ⟦0⟧ please."),), URLS)
    assert isinstance(checked, tuple)
    assert checked[0].untranslated


def test_a_surviving_token_is_restored_to_its_link_in_the_translation() -> None:
    checked = check_page((Block("p", ("Antrag ⟦0⟧ bitte",)),), (_p("Application ⟦0⟧ please"),), URLS)
    assert isinstance(checked, tuple)
    assert checked[0].block == Block("p", ("Application (https://a.de) please",))
    assert not checked[0].untranslated


def test_an_empty_translation_of_a_text_fails_that_block() -> None:
    checked = check_page((_p(GERMAN),), (_p("   "),), ())
    assert isinstance(checked, tuple)
    assert checked[0].untranslated


def test_a_length_ratio_outside_the_bounds_fails_that_block() -> None:
    checked = check_page((_p(GERMAN),), (_p("x" * 400),), ())
    assert isinstance(checked, tuple)
    assert checked[0].untranslated


def test_a_translation_over_4000_characters_is_untranslated() -> None:
    source = (_p(" ".join(["wort"] * 790)),)
    translated = (_p(" ".join(["wortwort"] * 460)),)
    checked = check_page(source, translated, ())
    assert isinstance(checked, tuple)
    assert checked[0].untranslated
    assert checked[0].block == source[0]


def test_control_characters_in_a_translation_are_removed_before_the_checks() -> None:
    checked = check_page((_p("Ergebnis gut."),), (_p("Ergebnis\x01 da."),), ())
    assert checked == (CheckedBlock(_p("Ergebnis da."), None),)


def test_a_cell_count_mismatch_fails_that_row() -> None:
    source = (Block("row", ("Name", "Wert")),)
    checked = check_page(source, (Block("row", ("Name",)),), ())
    assert isinstance(checked, tuple)
    assert checked[0].untranslated
