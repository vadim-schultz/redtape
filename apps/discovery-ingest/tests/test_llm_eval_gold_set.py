"""The committed real-page gold set: its coverage, its integrity and its offline cleaner recall (chapter E5)."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from discovery_ingest.extract.clean import clean_page
from discovery_ingest.extract.llm.evaluation.gold import GoldPage, load_gold, unknown_codes
from discovery_ingest.extract.llm.evaluation.metrics import cleaner_recall
from discovery_ingest.extract.llm.taxonomy import Taxonomy

GOLD_DIR = Path(__file__).parent / "fixtures" / "gold"
REQUIRED_KINDS = {"accordion", "list", "no-documents", "login-wall", "conditional"}
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE = re.compile(
    r"\+49 ?\(?\d\)?\d[\d \-()]{4,}\d|\+49\d{9,}|(?<![\w.])0800 ?\d[\d ]{5,}\d|(?<![\w.])0\d{2,4} [\d\- ]{5,}\d(?![.\d])"
)
MAX_FIXTURE_BYTES = 80_000
CLEANER_RECALL_FLOOR = 0.90


def _manifest() -> dict[str, dict[str, str]]:
    records = json.loads((GOLD_DIR / "manifest.json").read_text(encoding="utf-8"))
    return {record["name"]: record for record in records}


def _kinds() -> dict[str, set[str]]:
    records = json.loads((GOLD_DIR / "manifest.json").read_text(encoding="utf-8"))
    return {record["name"]: set(record["kinds"]) for record in records}


def _taxonomy() -> Taxonomy:
    return Taxonomy.model_validate_json((GOLD_DIR / "taxonomy.json").read_text(encoding="utf-8"))


def _hosts(pages: list[GoldPage]) -> set[str]:
    return {urlsplit(page.source_url).hostname or "" for page in pages}


def test_the_gold_set_has_about_twenty_pages_on_at_least_eight_hosts_and_every_required_kind() -> None:
    """gold set · coverage: 20 or so pages, 8 or more hosts, an accordion, a list, no documents, a login wall, conditions."""
    pages = load_gold(GOLD_DIR)
    kinds = set().union(*_kinds().values())

    assert 18 <= len(pages) <= 24
    assert len(_hosts(pages)) >= 8
    assert REQUIRED_KINDS <= kinds


def test_the_kind_tags_agree_with_the_labels() -> None:
    """gold set · a page tagged no-documents has none, conditional has a condition, login-wall is a login page."""
    all_kinds = _kinds()
    for page in load_gold(GOLD_DIR):
        kinds = all_kinds[page.name]
        assert ("no-documents" in kinds) == (not page.documents), page.name
        assert ("conditional" in kinds) == any(d.condition for d in page.documents), page.name
        assert ("login-wall" in kinds) == (page.page_kind == "login_or_error"), page.name
        assert ("list" in kinds) == (page.page_kind == "list"), page.name


def test_trimming_did_not_change_what_the_cleaner_reads() -> None:
    """gold set · clean_page of every committed page hashes to the value recorded from the untrimmed page at trim time."""
    manifest = _manifest()
    pages = load_gold(GOLD_DIR)

    assert set(manifest) == {page.name for page in pages}
    for page in pages:
        digest = hashlib.sha256(clean_page(page.html, page.source_url).text.encode()).hexdigest()
        assert digest == manifest[page.name]["cleaned_sha256"], page.name
        assert manifest[page.name]["source_url"] == page.source_url


def test_a_tampered_page_would_be_caught_by_the_trim_check() -> None:
    """gold set · the same digest differs as soon as one word of the page changes (the check can fail)."""
    page = load_gold(GOLD_DIR, limit=1)[0]
    original = hashlib.sha256(clean_page(page.html, page.source_url).text.encode()).hexdigest()
    tampered = clean_page(page.html.replace("</body>", "<p>Phantom</p></body>"), page.source_url).text

    assert hashlib.sha256(tampered.encode()).hexdigest() != original


def test_every_gold_code_is_in_the_real_taxonomy() -> None:
    """gold set · domain and situation codes exist in the vocabulary GET /machine/taxonomy serves."""
    taxonomy = _taxonomy()

    assert [
        (page.name, unknown_codes(page, taxonomy)) for page in load_gold(GOLD_DIR) if unknown_codes(page, taxonomy)
    ] == []


def test_a_code_outside_the_taxonomy_is_reported() -> None:
    """unknown_codes · a made-up code is returned by name; a known one is not."""
    page = load_gold(GOLD_DIR, limit=1)[0].model_copy(update={"domain_codes": ("housing", "made-up")})

    assert unknown_codes(page, _taxonomy()) == ["made-up"]


def test_the_committed_html_holds_no_email_address_or_phone_number() -> None:
    """gold set · personal data is removed: only the placeholder address and number remain."""
    for path in GOLD_DIR.glob("*.html"):
        text = path.read_text(encoding="utf-8")
        assert {mail for mail in EMAIL.findall(text) if not mail.endswith("@example.invalid")} <= {
            "friendly-challenge@0.9.19",
            "sdk@0.1.31",
        }, path.name
        assert {phone for phone in PHONE.findall(text) if phone != "0000 0000000"} == set(), path.name


def test_the_personal_data_patterns_do_catch_a_real_looking_number_and_address() -> None:
    """gold set · the guard patterns match a mailbox and a landline, so a clean result means something."""
    assert EMAIL.findall("Schreiben Sie an erika.mustermann@behoerde.example") != []
    assert PHONE.findall("Telefon 0228 6845-2227") != []


def test_each_fixture_stays_reviewable_in_size() -> None:
    """gold set · every html page is under 80 KB after trimming."""
    sizes = {path.name: path.stat().st_size for path in GOLD_DIR.glob("*.html")}

    assert sizes and all(size <= MAX_FIXTURE_BYTES for size in sizes.values()), sizes


def test_the_cleaner_keeps_nearly_every_gold_name_on_the_real_pages() -> None:
    """gold set · offline cleaner_recall over the real pages stays above the floor (measured 44 of 47 names, 0.936)."""
    pages = [
        (page.name, [d.name for d in page.documents], clean_page(page.html, page.source_url).text)
        for page in load_gold(GOLD_DIR)
    ]

    assert cleaner_recall([(names, text) for _name, names, text in pages]) >= CLEANER_RECALL_FLOOR


def test_a_missing_gold_name_would_pull_cleaner_recall_below_the_floor() -> None:
    """gold set · three invented names on a 47-name set drop the recall by more than the floor allows."""
    page = load_gold(GOLD_DIR, limit=1)[0]
    text = clean_page(page.html, page.source_url).text

    assert cleaner_recall([(["Phantom eins", "Phantom zwei"], text)]) < CLEANER_RECALL_FLOOR


def test_the_js_shell_page_cleans_to_nothing() -> None:
    """gold set · an un-rendered client-side shell has no text, so the model must not be paid for it."""
    page = next(page for page in load_gold(GOLD_DIR) if page.name == "verwaltung-js-shell")

    assert clean_page(page.html, page.source_url).text.strip() == ""
