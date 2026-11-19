"""Fused-render canary comparison: identical hashes, text loss, lost links and the 90% verdict (chapter 8)."""

from __future__ import annotations

from discovery_ingest.browser.canary import PageCompare, compare_page, judge

BASE = "https://portal.example/service/1"
PARAGRAPH = "Wer einen Wohnsitz in der Stadt hat, kann den Antrag online stellen und die Unterlagen hochladen."
LONG = " ".join([PARAGRAPH] * 4)


def _page(*paragraphs: str, links: tuple[str, ...] = ("/antrag",)) -> str:
    """Return a small recorded-style page: a title, a main region with the paragraphs and one link per href."""
    body = "".join(f"<p>{text}</p>" for text in paragraphs)
    anchors = "".join(f'<a href="{href}">Antrag</a>' for href in links)
    return (
        '<html lang="de"><head><title>Leistung</title></head><body><main><h1>Leistung</h1>'
        f"{body}{anchors}</main></body></html>"
    )


def _measured(identical: bool = True, text_loss: float = 0.0, links: tuple[int, int] = (1, 1)) -> PageCompare:
    return PageCompare(
        identical=identical,
        text_loss=text_loss,
        content_blocks=3,
        fused_blocks=3,
        content_links=links[0],
        fused_links=links[1],
    )


def test_identical_dom_pages_are_identical_with_no_loss_and_the_same_links() -> None:
    """canary · the same DOM in both calls: the hashes match, nothing is lost and the link count is kept."""
    page = compare_page(_page(LONG), _page(LONG), BASE)

    assert page.identical is True
    assert page.text_loss == 0.0
    assert (page.content_links, page.fused_links, page.lost_link) == (1, 1, False)


def test_extra_dynamic_text_changes_the_hash_but_loses_nothing() -> None:
    """canary · a timestamp only the fused DOM shows is a hash mismatch, not a loss of text or links."""
    page = compare_page(_page(LONG), _page(LONG, "Stand: 12.11.2026 10:00"), BASE)

    assert page.identical is False
    assert page.text_loss == 0.0
    assert page.lost_link is False


def test_a_fused_dom_missing_half_its_text_reports_the_loss() -> None:
    """canary · dropping a paragraph from the fused DOM is a text loss the gate reads, not a silent match."""
    page = compare_page(_page(LONG, LONG), _page(LONG), BASE)

    assert page.identical is False
    assert page.text_loss > 0.4


def test_a_fused_dom_without_a_link_is_a_lost_link() -> None:
    """canary · the fused DOM has fewer links than the /content DOM: lost_link is set."""
    page = compare_page(_page(LONG), _page(LONG, links=()), BASE)

    assert (page.content_links, page.fused_links, page.lost_link) == (1, 0, True)


def test_the_canary_passes_at_nine_identical_pages_out_of_ten() -> None:
    """canary · 90% identical with nothing lost passes."""
    pages = [_measured() for _ in range(9)] + [_measured(identical=False)]

    verdict = judge(pages, required=10)

    assert (verdict.pages, verdict.identical, verdict.passed) == (10, 9, True)


def test_the_canary_fails_below_ninety_percent_identical() -> None:
    """canary · eight of ten identical is below 90%: the gate fails even with nothing lost."""
    pages = [_measured() for _ in range(8)] + [_measured(identical=False) for _ in range(2)]

    verdict = judge(pages, required=10)

    assert (verdict.identical, verdict.passed) == (8, False)


def test_the_canary_fails_when_one_page_loses_more_than_five_percent_of_its_text() -> None:
    """canary · one page losing 20% of its text fails the gate, whatever the hash share is."""
    pages = [_measured() for _ in range(9)] + [_measured(text_loss=0.2)]

    assert judge(pages, required=10).passed is False


def test_the_canary_passes_at_exactly_five_percent_text_loss_and_fails_on_any_lost_link() -> None:
    """canary · a 5% loss is the limit and still passes; a single lost link fails the gate."""
    at_limit = [_measured(text_loss=0.05) for _ in range(10)]
    with_lost_link = [_measured() for _ in range(9)] + [_measured(links=(2, 1))]

    assert judge(at_limit, required=10).passed is True
    assert judge(with_lost_link, required=10).passed is False


def test_the_canary_fails_when_fewer_stable_pages_than_required_were_measured() -> None:
    """canary · nine measured pages do not satisfy a request for twelve: the gate fails, it does not shrink."""
    pages = [_measured() for _ in range(9)]

    assert judge(pages, required=12).passed is False
    assert judge([], required=1).passed is False
