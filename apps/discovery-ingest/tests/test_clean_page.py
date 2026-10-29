"""Page cleaner: boilerplate removal and main-region choice on small inline HTML."""

from __future__ import annotations

import pytest
from discovery_ingest.extract.clean import clean_page

BASE = "https://portal.example/dienst/reisepass"
LONG_PARAGRAPH = "Bitte bringen Sie alle erforderlichen Unterlagen zum Termin mit. " * 12


def _page(body: str, head: str = "") -> str:
    return f"<html><head>{head}</head><body>{body}</body></html>"


def test_boilerplate_elements_and_hidden_elements_are_dropped() -> None:
    html = _page(
        "<script>var tracking = 1;</script><style>p { color: red }</style><noscript>Bitte JavaScript</noscript>"
        "<template><p>Vorlage</p></template><svg><text>Symbol</text></svg>"
        "<header><p>Kopfzeile</p></header><nav><a href='/a'>Menue</a></nav>"
        "<aside>Randspalte</aside><form><label>Suchbegriff</label></form>"
        "<div id='cookie-banner'>Cookies akzeptieren</div><div class='ConsentDialog'>Zustimmung</div>"
        "<div class='site-search'>Suche</div><ul class='breadcrumb'><li>Start</li></ul>"
        "<p hidden>Versteckt</p><p aria-hidden='true'>Dekoration</p>"
        "<p>Personalausweis mitbringen</p><footer>Impressum</footer>"
    )
    text = clean_page(html, BASE).text
    assert text == "Personalausweis mitbringen"


def test_ordinary_elements_with_lookalike_names_are_kept() -> None:
    html = _page(
        "<div class='researchers'>Forschende</div><section id='content'><p aria-hidden='false'>Sichtbar</p></section>"
    )
    assert clean_page(html, BASE).text == "Forschende\nSichtbar"


def test_main_region_is_preferred_when_long_enough() -> None:
    html = _page(f"<p>Randtext</p><main><p>{LONG_PARAGRAPH}</p></main>")
    text = clean_page(html, BASE).text
    assert "Randtext" not in text
    assert "erforderlichen Unterlagen" in text


@pytest.mark.parametrize("opening", ["<main>", "<div role='main'>", "<article>"])
def test_body_is_used_when_the_main_region_is_short(opening: str) -> None:
    closing = {"<main>": "</main>", "<article>": "</article>"}.get(opening, "</div>")
    html = _page(f"<p>Randtext</p>{opening}<p>Kurz</p>{closing}")
    assert clean_page(html, BASE).text == "Randtext\nKurz"


@pytest.mark.parametrize("opening", ["<div role='main'>", "<article>"])
def test_role_main_and_a_single_article_are_preferred_when_long(opening: str) -> None:
    closing = "</article>" if opening == "<article>" else "</div>"
    html = _page(f"<p>Randtext</p>{opening}<p>{LONG_PARAGRAPH}</p>{closing}")
    assert "Randtext" not in clean_page(html, BASE).text


def test_several_articles_do_not_narrow_the_page_to_the_first() -> None:
    html = _page(f"<article><p>{LONG_PARAGRAPH}</p></article><article><p>Zweite Karte</p></article>")
    assert "Zweite Karte" in clean_page(html, BASE).text


def test_forms_are_kept_inside_the_main_region_and_dropped_outside_it() -> None:
    html = _page(f"<form><p>Kopfformular</p></form><main><form><p>Antrag {LONG_PARAGRAPH}</p></form></main>")
    text = clean_page(html, BASE).text
    assert "Kopfformular" not in text
    assert text.startswith("Antrag")


def test_a_form_wrapping_the_whole_page_is_not_dropped() -> None:
    html = _page("<form id='aspnetForm'><p>Personalausweis</p><p>Meldebescheinigung</p></form>")
    assert clean_page(html, BASE).text == "Personalausweis\nMeldebescheinigung"


def test_headings_list_items_table_rows_and_links_become_compact_markdown() -> None:
    html = _page(
        "<h1> Reisepass  beantragen </h1><p>Intro  text</p><h2>Unterlagen</h2>"
        "<ul><li>Personalausweis</li><li>Foto <a href='/foto'>Muster</a></li></ul>"
        "<table><tr><th>Dokument</th><th>Frist</th></tr><tr><td>Meldebescheinigung</td><td>3 Monate</td></tr></table>"
        "<dl><dt>Gebühr</dt><dd>60 Euro</dd></dl>"
        "<p>Formular: <a href='antrag.pdf#seite2'>Antrag</a></p>"
    )
    assert clean_page(html, BASE).text.splitlines() == [
        "# Reisepass beantragen",
        "Intro text",
        "## Unterlagen",
        "- Personalausweis",
        "- Foto Muster (https://portal.example/foto)",
        "Dokument | Frist",
        "Meldebescheinigung | 3 Monate",
        "Gebühr: 60 Euro",
        "Formular: Antrag (https://portal.example/dienst/antrag.pdf)",
    ]


def test_nested_list_items_get_their_own_lines() -> None:
    html = _page("<ul><li>Eltern<ul><li>Vater</li><li>Mutter</li></ul></li></ul>")
    assert clean_page(html, BASE).text.splitlines() == ["- Eltern", "- Vater", "- Mutter"]


@pytest.mark.parametrize("href", ["mailto:amt@portal.example", "javascript:void(0)", "#oben", "tel:+4930123"])
def test_links_that_are_not_http_pages_keep_their_text_only(href: str) -> None:
    html = _page(f"<p>Kontakt: <a href='{href}'>Amt</a></p>")
    assert clean_page(html, BASE).text == "Kontakt: Amt"


def test_a_link_whose_text_is_its_url_is_not_repeated() -> None:
    html = _page("<p><a href='https://portal.example/a'>https://portal.example/a</a></p>")
    assert clean_page(html, BASE).text == "https://portal.example/a"


def test_empty_cells_and_empty_rows_leave_no_trace() -> None:
    html = _page("<table><tr><td></td><td>Frist</td></tr><tr><td> </td><td></td></tr></table>")
    assert clean_page(html, BASE).text == "Frist"


def test_output_is_deterministic_and_collapses_whitespace_and_duplicate_lines() -> None:
    html = _page("<p>Hinweis</p><p>Hinweis</p><p>A&nbsp;&nbsp;\n B</p><p>Hinweis</p><p>Hinweis</p>")
    first = clean_page(html, BASE)
    assert first == clean_page(html, BASE)
    assert first.text.splitlines() == ["Hinweis", "A B", "Hinweis"]


def test_links_include_anchors_outside_the_kept_region_and_exclude_non_pages() -> None:
    body = (
        "<nav><a href='/start'>Start</a></nav><div id='cookie-banner'><a href='https://cdn.example/datenschutz'>D</a></div>"
        f"<p hidden><a href='/versteckt'>V</a></p><main><p>{LONG_PARAGRAPH}</p>"
        "<a href='antrag.pdf#seite2'>Antrag</a><a href='/start'>Start nochmal</a>"
        "<a href='mailto:amt@portal.example'>Mail</a><a href='javascript:void(0)'>Los</a>"
        "<a href='#oben'>Nach oben</a><a href='ftp://files.example/a'>FTP</a><a>Ohne Ziel</a></main>"
        "<footer><a href='//other.example/impressum'>Impressum</a></footer>"
    )
    assert clean_page(_page(body), BASE).links == frozenset(
        {
            "https://portal.example/start",
            "https://cdn.example/datenschutz",
            "https://portal.example/versteckt",
            "https://portal.example/dienst/antrag.pdf",
            "https://other.example/impressum",
        }
    )


def test_a_page_without_anchors_has_no_links() -> None:
    assert clean_page(_page("<p>Text</p>"), BASE).links == frozenset()


@pytest.mark.parametrize(("lang", "expected"), [("de-DE", "de"), ("EN", "en"), ("de_AT", "de"), (" fr ", "fr")])
def test_language_is_read_from_the_html_lang_attribute(lang: str, expected: str) -> None:
    assert clean_page(f"<html lang='{lang}'><body><p>x</p></body></html>", BASE).language == expected


@pytest.mark.parametrize(
    "html", ["<html><body><p>x</p></body></html>", "<html lang=''><body></body></html>", "<p>x</p>"]
)
def test_language_is_none_when_absent_or_empty(html: str) -> None:
    assert clean_page(html, BASE).language is None


def test_title_is_collapsed_and_none_when_absent() -> None:
    titled = clean_page(_page("<p>x</p>", "<title> Reisepass\n beantragen </title>"), BASE)
    assert titled.title == "Reisepass beantragen"
    assert clean_page(_page("<p>x</p>"), BASE).title is None


@pytest.mark.parametrize(
    "html",
    ["", "   \n", "<html><body></body></html>", "<body><script>x = 1</script></body>", "<div><p>", "<a href='"],
)
def test_empty_or_malformed_html_returns_empty_text_without_raising(html: str) -> None:
    page = clean_page(html, BASE)
    assert (page.text, page.links, page.truncated) == ("", frozenset(), False)


def test_unterminated_markup_still_yields_its_text() -> None:
    assert clean_page("<div><p>Personalausweis <b>mitbringen", BASE).text == "Personalausweis mitbringen"


def test_absurdly_deep_nesting_returns_empty_text_without_raising() -> None:
    html = "<div>" * 5000 + "Text" + "</div>" * 5000
    assert clean_page(html, BASE).text == ""


def test_line_breaks_split_a_paragraph_into_lines() -> None:
    assert clean_page(_page("<p>Straße 1<br>12345 Musterstadt<br/><br>Tel. 115</p>"), BASE).text.splitlines() == [
        "Straße 1",
        "12345 Musterstadt",
        "Tel. 115",
    ]


def test_a_link_with_a_strong_title_and_a_block_description_keeps_a_space_between_them() -> None:
    """whitespace · the title and the description of one download link are two words, not one fused word."""
    link = "<a href='/f.pdf'><strong>Antragsformular Ferienbeschäftigung</strong><div>Formular für den Arbeitgeber</div></a>"
    text = clean_page(_page(f"<ul><li>{link}</li></ul>"), BASE).text
    assert "Antragsformular Ferienbeschäftigung Formular für den Arbeitgeber" in text


def test_inline_elements_inside_a_link_stay_joined_and_blocks_in_a_table_cell_are_separated() -> None:
    """whitespace · only block children add a space: ``<strong>Antrag</strong>formular`` is still one word."""
    html = _page(
        "<p><a href='/f'><strong>Antrag</strong>formular</a></p><table><tr><td><p>Name</p><p>Ort</p></td></tr></table>"
    )
    assert clean_page(html, BASE).text == "Antragformular (https://portal.example/f)\nName Ort"


def test_the_cleaner_version_is_clean_4() -> None:
    """version · screen-reader text is dropped, so cached answers of clean-3 are not reused."""
    assert clean_page(_page("<p>Text</p>"), BASE).version == "clean-4"


@pytest.mark.parametrize(
    "token", ["sr-only", "visually-hidden", "visuallyhidden", "screen-reader-text", "show-for-sr", "u-sr-only"]
)
def test_a_span_with_a_screen_reader_only_class_is_dropped_with_its_text(token: str) -> None:
    """helper text · ``<span class="sr-only">positiv:</span>`` is not page text, so the bullet reads without it."""
    html = _page(f"<ul><li><span class='row {token}'>positiv:</span>Kundennummer</li></ul>")
    assert clean_page(html, BASE).text == "- Kundennummer"


def test_a_doubled_label_made_of_visible_text_and_a_screen_reader_copy_is_printed_once() -> None:
    """helper text · ``Wichtig:Wichtig:`` came from a screen-reader copy next to the visible label."""
    html = _page("<p><span class='sr-only'>Wichtig:</span><strong>Wichtig:</strong> Ohne Bestätigung kein Zugang.</p>")
    assert clean_page(html, BASE).text == "Wichtig: Ohne Bestätigung kein Zugang."


@pytest.mark.parametrize(
    "attributes",
    [
        "id='sr-only'",
        "class='sr-only-label'",
        "class='no-sr-only'",
        "class='visually-hidden-focusable-not'",
        "data-x='sr-only'",
    ],
)
def test_a_visible_element_whose_name_merely_contains_sr_only_is_kept(attributes: str) -> None:
    """helper text · whole class tokens only: lookalike ids, classes and attributes keep their text."""
    html = _page(f"<p>Hinweis <span {attributes}>Personalausweis</span> mitbringen und sr-only lesen</p>")
    assert clean_page(html, BASE).text == "Hinweis Personalausweis mitbringen und sr-only lesen"


@pytest.mark.parametrize(
    "markup",
    [
        "<body class='sr-only'><p>Hauptinhalt</p></body>",
        "<body><main class='visually-hidden'><p>Hauptinhalt</p></main></body>",
        "<body><div class='sr-only'><main><p>Hauptinhalt</p></main></div></body>",
        "<body><div class='u-sr-only'><article><p>Hauptinhalt</p></article></div></body>",
    ],
)
def test_the_page_body_and_the_main_region_are_never_dropped_by_the_helper_text_rule(markup: str) -> None:
    """helper text · a class on ``body``, ``main`` or a wrapper of the main content does not empty the page."""
    assert clean_page(f"<html><head></head>{markup}</html>", BASE).text == "Hauptinhalt"
