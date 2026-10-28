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
