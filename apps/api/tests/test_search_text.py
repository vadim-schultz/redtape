"""The pure search-text recipe (chapter 4): selection, normalisation, truncation."""

from __future__ import annotations

import unicodedata
import uuid

from app.features.search.hashing import content_hash
from app.features.search.text import (
    MAX_CHARS,
    MAX_EXCERPTS,
    TS_CONFIG_BY_LOCALE,
    MentionExcerpt,
    build,
)
from app.shared.locale import SUPPORTED_LOCALE_CODES


def _mention(n: int, excerpt: str = "Text", score: float | None = None) -> MentionExcerpt:
    return MentionExcerpt(id=uuid.UUID(int=n), excerpt=excerpt, score=score)


def _text(title: dict[str, str], *mentions: MentionExcerpt, locale: str = "de") -> str:
    built = build(title, mentions, locale)
    assert built is not None
    return built.text


def test_same_inputs_always_give_the_same_text_and_hash_including_ties() -> None:
    mentions = [_mention(3, "drei", 0.5), _mention(1, "eins", 0.5), _mention(2, "zwei", 0.5)]

    first = build({"de": "Antrag"}, mentions, "de")
    second = build({"de": "Antrag"}, list(reversed(mentions)), "de")

    assert first is not None and second is not None
    assert first.text == second.text == "Antrag eins zwei drei"
    assert first.content_hash == second.content_hash == content_hash(first.text)


def test_excerpts_are_ordered_by_score_descending_then_id_with_unscored_last() -> None:
    mentions = [_mention(1, "ohne"), _mention(2, "niedrig", 0.2), _mention(3, "hoch", 0.9)]

    assert _text({"de": "T"}, *mentions) == "T hoch niedrig ohne"


def test_only_the_best_excerpts_are_used() -> None:
    mentions = [_mention(n, f"e{n}", score=n / 10) for n in range(1, MAX_EXCERPTS + 3)]

    text = _text({"de": "T"}, *mentions)

    assert text.split() == ["T", *[f"e{n}" for n in range(MAX_EXCERPTS + 2, 2, -1)]]


def test_title_prefers_de_then_en_then_any_value() -> None:
    assert _text({"en": "Apply", "de": "Antrag"}) == "Antrag"
    assert _text({"en": "Apply", "fr": "Demande"}) == "Apply"
    assert _text({"de": "  ", "fr": "Demande"}) == "Demande"


def test_text_is_nfc_normalised_and_whitespace_collapsed() -> None:
    decomposed = unicodedata.normalize("NFD", "Kinder geld  für\n\tEltern")

    text = _text({"de": " Antrag "}, _mention(1, decomposed))

    assert text == unicodedata.normalize("NFC", "Antrag Kinder geld für Eltern")


def test_text_is_truncated_on_a_word_boundary_within_the_limit() -> None:
    long_excerpt = " ".join(["Wort"] * 1000)

    text = _text({"de": "Titel"}, _mention(1, long_excerpt))

    assert len(text) <= MAX_CHARS
    assert text.endswith("Wort") and "Wor " not in text
    assert len(text) > MAX_CHARS - len("Wort ")


def test_a_single_overlong_word_is_cut_at_the_limit() -> None:
    assert len(_text({"de": "x" * (MAX_CHARS + 50)})) == MAX_CHARS


def test_no_title_and_no_excerpts_builds_nothing() -> None:
    assert build({}, [], "de") is None
    assert build({"de": "   "}, [_mention(1, " \n ")], "de") is None


def test_excerpts_alone_are_usable_text() -> None:
    assert _text({}, _mention(1, "Bitte Ausweis mitbringen")) == "Bitte Ausweis mitbringen"


def test_every_supported_locale_has_one_text_search_configuration() -> None:
    assert set(TS_CONFIG_BY_LOCALE) == SUPPORTED_LOCALE_CODES
    assert TS_CONFIG_BY_LOCALE["de"] == "german"
    assert TS_CONFIG_BY_LOCALE["pl"] == TS_CONFIG_BY_LOCALE["uk"] == "simple"
