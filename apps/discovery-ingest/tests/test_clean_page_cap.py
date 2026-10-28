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


def _menu(*, links: int) -> str:
    """A navigation block outside ``nav``: a heading and a bare list of links, no sentence."""
    items = "".join(f"<li><a href='/m{index}'>Punkt {index}</a></li>" for index in range(links))
    return f"<h2>Wegweiser</h2><ul>{items}</ul>"


def test_under_the_cap_sections_inside_main_are_kept_before_sections_outside_it() -> None:
    """cap · a short main is not the whole page, but its sections still outrank a priority section outside it."""
    inside = "## Gebühren\nSechzig Euro"
    outside = "## Formulare\nAntrag auf Reisepass"
    html = "<html><body><h2>Formulare</h2><p>Antrag auf Reisepass</p><main><h2>Gebühren</h2><p>Sechzig Euro</p></main></body></html>"
    page = clean_page(html, BASE, max_chars=len(inside))
    assert (page.text, page.truncated) == (inside, True)
    assert outside not in page.text


def test_the_largest_article_counts_as_main_and_a_page_without_either_keeps_its_priority_order() -> None:
    """cap · among several articles the longest ranks first; with no main or article priority headings decide."""
    articles = "<article><h2>Kontakt</h2><p>Telefon 115</p></article><article><h2>Gebühren</h2><p>Sechzig Euro netto</p></article>"
    page = clean_page(f"<html><body>{articles}</body></html>", BASE, max_chars=len("## Gebühren\nSechzig Euro netto"))
    assert page.text == "## Gebühren\nSechzig Euro netto"
    plain = clean_page(_html(GENERAL, DOCUMENTS), BASE, max_chars=len(DOCUMENTS))
    assert plain.text == DOCUMENTS


def test_a_long_list_of_bare_links_outside_nav_ranks_below_prose_under_the_cap() -> None:
    """cap · twelve bare links with no sentence give way to prose that comes later on the page."""
    prose = "## Hinweise\nBitte bringen Sie den Personalausweis mit."
    html = (
        f"<html><body>{_menu(links=12)}<h2>Hinweise</h2><p>Bitte bringen Sie den Personalausweis mit.</p></body></html>"
    )
    page = clean_page(html, BASE, max_chars=len(prose))
    assert (page.text, page.truncated) == (prose, True)


def test_a_list_of_ten_links_or_a_long_list_with_sentences_keeps_its_document_order() -> None:
    """cap · only more than ten links with no sentence text count as a menu."""
    prose = "## Hinweise\nBitte bringen Sie den Personalausweis mit."
    ten = clean_page(f"<html><body>{_menu(links=10)}{_html(prose)}</body></html>", BASE, max_chars=200)
    assert ten.text.startswith("## Wegweiser")
    sentence = "<li>Bitte bringen Sie den Personalausweis zum Termin mit.</li>"
    wordy = f"<html><body><h2>Wegweiser</h2><ul>{sentence * 12}</ul><h2>Hinweise</h2><p>Zweiter Abschnitt hier.</p></body></html>"
    page = clean_page(
        wordy,
        BASE,
        max_chars=len("## Wegweiser") + 12 * (len("- Bitte bringen Sie den Personalausweis zum Termin mit.") + 1),
    )
    assert page.text.startswith("## Wegweiser")


def test_a_list_of_downloads_with_file_sizes_is_not_a_menu(monkeypatch: pytest.MonkeyPatch) -> None:
    """cap · twelve links that each name a file with its size are documents, so they keep their place under the cap."""
    items = "".join(f"<li><a href='/d{index}.pdf'>Anlage {index} (PDF, 10 KB)</a></li>" for index in range(12))
    downloads = "## Anlagen\n" + "\n".join(
        f"- Anlage {index} (PDF, 10 KB) (https://portal.example/d{index}.pdf)" for index in range(12)
    )
    html = f"<html><body><h2>Anlagen</h2><ul>{items}</ul><h2>Hinweise</h2><p>Bitte bringen Sie den Personalausweis mit.</p></body></html>"
    page = clean_page(html, BASE, max_chars=len(downloads))
    assert page.text == downloads
