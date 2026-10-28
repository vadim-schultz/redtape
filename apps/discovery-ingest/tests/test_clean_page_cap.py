"""Page cleaner cap: section prioritisation under a character budget, never cutting a line."""

from __future__ import annotations

import pytest
from discovery_ingest.extract.clean import clean_page

BASE = "https://portal.example/dienst/reisepass"
GENERAL = "## Allgemeines\nAllgemeine Hinweise"
CONTACT = "## Kontakt\nTelefon 115"
DOCUMENTS = "## Erforderliche Unterlagen\nPersonalausweis\nMeldebescheinigung"


def _html(*sections: str) -> str:
    """Build a page from markdown-like sections: ``## heading`` then one paragraph per line."""
    parts = []
    for section in sections:
        heading, *lines = section.splitlines()
        parts.append(f"<h2>{heading.removeprefix('## ')}</h2>" + "".join(f"<p>{line}</p>" for line in lines))
    return f"<html><body>{''.join(parts)}</body></html>"


def _text(*sections: str) -> str:
    return "\n".join(sections)


@pytest.mark.parametrize("slack", [0, 1, 500])
def test_text_within_the_cap_is_returned_whole_with_truncated_false(slack: int) -> None:
    full = _text(GENERAL, DOCUMENTS)
    page = clean_page(_html(GENERAL, DOCUMENTS), BASE, max_chars=len(full) + slack)
    assert (page.text, page.truncated) == (full, False)


def test_text_one_character_over_the_cap_is_truncated() -> None:
    full = _text(GENERAL, DOCUMENTS)
    assert clean_page(_html(GENERAL, DOCUMENTS), BASE, max_chars=len(full) - 1).truncated is True


def test_over_the_cap_sections_with_priority_headings_are_kept_first() -> None:
    page = clean_page(_html(GENERAL, CONTACT, DOCUMENTS), BASE, max_chars=len(DOCUMENTS))
    assert (page.text, page.truncated) == (DOCUMENTS, True)


def test_kept_sections_stay_in_document_order() -> None:
    forms = "## Formulare\nAntrag auf Reisepass"
    page = clean_page(_html(GENERAL, forms, CONTACT, DOCUMENTS), BASE, max_chars=len(_text(forms, DOCUMENTS)))
    assert page.text == _text(forms, DOCUMENTS)


@pytest.mark.parametrize(
    "heading",
    [
        "Unterlagen",
        "Nachweise",
        "Voraussetzungen",
        "Formulare",
        "Erforderlich",
        "Was Sie mitbringen",
        "Antrag",
        "Dokumente",
    ],
)
def test_every_priority_word_marks_a_heading_as_priority(heading: str) -> None:
    section = f"## {heading}\nBeleg"
    page = clean_page(_html(GENERAL, section), BASE, max_chars=len(section))
    assert page.text == section


def test_a_page_with_no_priority_headings_keeps_the_leading_sections_in_order() -> None:
    page = clean_page(_html(GENERAL, CONTACT, "## Gebühren\n60 Euro"), BASE, max_chars=len(_text(GENERAL, CONTACT)))
    assert page.text == _text(GENERAL, CONTACT)


def test_a_priority_word_in_the_body_text_does_not_promote_a_section() -> None:
    sneaky = "## Gebühren\nBringen Sie Unterlagen mit"
    page = clean_page(_html(GENERAL, sneaky), BASE, max_chars=len(GENERAL))
    assert page.text == GENERAL


@pytest.mark.parametrize("max_chars", range(1, len(_text(GENERAL, CONTACT, DOCUMENTS))))
def test_the_cap_never_cuts_a_line_and_truncated_is_true(max_chars: int) -> None:
    sections = (GENERAL, CONTACT, DOCUMENTS)
    page = clean_page(_html(*sections), BASE, max_chars=max_chars)
    original_lines = set(_text(*sections).splitlines())
    assert page.truncated is True
    assert len(page.text) <= max_chars
    assert set(page.text.splitlines()) <= original_lines


def test_a_single_line_longer_than_the_cap_is_dropped_not_cut() -> None:
    page = clean_page(_html("## Unterlagen\n" + "Lang " * 40), BASE, max_chars=50)
    assert page.text == "## Unterlagen"
    assert page.truncated is True
