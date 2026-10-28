"""RFC 9309 matching: longest rule wins, allow wins ties, ``*`` and ``$`` patterns, group selection."""

from __future__ import annotations

import random

import pytest
from discovery_ingest.worker.robots_rules import RobotsRules

AGENT = "RedtapeBot"
HOST = "https://site.example"


def _rules(text: str, agent: str = AGENT) -> RobotsRules:
    return RobotsRules.parse(text.splitlines(), agent)


def _verdicts(rules: RobotsRules, *paths: str) -> list[bool]:
    return [rules.allowed(f"{HOST}{path}") for path in paths]


@pytest.mark.parametrize(
    ("text", "path", "expected"),
    [
        ("User-agent: *\nDisallow: /\nAllow: /DPMAregister/Uebersicht", "/DPMAregister/Uebersicht", True),
        ("User-agent: *\nAllow: /DPMAregister/Uebersicht\nDisallow: /", "/DPMAregister/Uebersicht", True),
        ("User-agent: *\nDisallow: /\nAllow: /DPMAregister/Uebersicht", "/other", False),
        ("User-agent: *\nDisallow: /SiteGlobals/\nAllow: /SiteGlobals/Modules/", "/SiteGlobals/Modules/x", True),
        ("User-agent: *\nAllow: /a\nDisallow: /a/b", "/a/b/c", False),
    ],
    ids=["dpma", "dpma-reordered", "dpma-negative", "bafin", "longer-disallow-beats-shorter-allow"],
)
def test_a_longer_rule_beats_a_shorter_one_regardless_of_order_in_the_file(
    text: str, path: str, expected: bool
) -> None:
    """a longer allow beats a shorter disallow regardless of order in the file."""
    assert _rules(text).allowed(f"{HOST}{path}") is expected


def test_on_equal_length_allow_wins() -> None:
    """on equal length allow wins."""
    for text in ("User-agent: *\nAllow: /page\nDisallow: /page", "User-agent: *\nDisallow: /page\nAllow: /page"):
        assert _rules(text).allowed(f"{HOST}/page") is True


def test_on_unequal_length_the_longer_disallow_is_not_rescued_by_allow() -> None:
    """a disallow longer than the matching allow still blocks (negative for the tie rule)."""
    assert _rules("User-agent: *\nAllow: /pag\nDisallow: /page").allowed(f"{HOST}/page") is False


def test_a_trailing_dollar_anchors_the_end_of_the_url() -> None:
    """a trailing dollar anchors the end of the url."""
    home = _rules("User-agent: *\nDisallow: /\nAllow: /$")
    pdf = _rules("User-agent: *\nDisallow: /*.pdf$")

    assert _verdicts(home, "/", "/anything-else") == [True, False]
    assert _verdicts(pdf, "/a.pdf", "/a.pdf?x=1", "/a.pdfx", "/dir/b.pdf") == [False, True, True, False]


def test_a_star_matches_any_run_of_characters_including_slashes() -> None:
    """a star matches any run of characters including slashes."""
    rules = _rules("User-agent: *\nDisallow: /*/private/*.html")

    assert _verdicts(rules, "/a/b/private/c/d.html", "/private/x.html", "/a/private/x.txt") == [False, True, True]


def test_the_query_string_takes_part_in_matching() -> None:
    """matching runs against path plus query string."""
    rules = _rules("User-agent: *\nDisallow: /*?session=")

    assert _verdicts(rules, "/page?session=1", "/page?other=1", "/page") == [False, True, True]


def test_percent_encodings_compare_case_insensitively_on_the_hex_digits() -> None:
    """percent-encodings compare case-insensitively on the hex digits; nothing else is normalised."""
    rules = _rules("User-agent: *\nDisallow: /caf%c3%a9")

    assert _verdicts(rules, "/caf%C3%A9", "/Caf%C3%A9", "/cafe") == [False, True, True]


def test_an_empty_disallow_allows_everything_and_an_empty_allow_blocks_nothing() -> None:
    """an empty disallow allows everything and an empty allow blocks nothing."""
    assert _rules("User-agent: *\nDisallow:").allowed(f"{HOST}/any") is True
    assert _rules("User-agent: *\nAllow:").allowed(f"{HOST}/any") is True
    assert _rules("User-agent: *\nDisallow: /x\nDisallow:").allowed(f"{HOST}/x") is False


GROUPS = """\
User-agent: *
Disallow: /

User-agent: Redtape
Disallow: /short

User-agent: RedtapeBot
Disallow: /long
"""


def test_the_most_specific_user_agent_group_wins_and_falls_back_to_the_star_group() -> None:
    """the most specific user agent group wins and falls back to the star group."""
    assert _verdicts(_rules(GROUPS), "/long", "/short", "/free") == [False, True, True]
    assert _verdicts(_rules(GROUPS, "RedtapeProbe"), "/short", "/long") == [False, True]
    assert _verdicts(_rules(GROUPS, "Other"), "/free") == [False]


def test_agent_matching_is_case_insensitive_and_consecutive_agent_lines_share_rules() -> None:
    """consecutive User-agent lines share one rule list, whatever their case."""
    rules = _rules("user-AGENT: googlebot\nUSER-AGENT: REDTAPEBOT\nDISALLOW: /x\n")

    assert _verdicts(rules, "/x", "/y") == [False, True]


def test_groups_naming_the_same_agent_are_merged() -> None:
    """groups naming the same agent are merged."""
    rules = _rules("User-agent: RedtapeBot\nDisallow: /a\n\nUser-agent: redtapebot\nDisallow: /b\n")

    assert _verdicts(rules, "/a", "/b", "/c") == [False, False, True]


def test_no_matching_group_and_no_star_group_allows_everything() -> None:
    """no matching group and no star group allows everything."""
    rules = _rules("User-agent: Googlebot\nDisallow: /\n")

    assert _verdicts(rules, "/", "/x") == [True, True]


def test_a_matching_group_is_not_diluted_by_the_star_group() -> None:
    """a named group replaces the star group; it does not add to it (negative for the fallback)."""
    rules = _rules("User-agent: *\nDisallow: /star\n\nUser-agent: RedtapeBot\nDisallow: /own\n")

    assert _verdicts(rules, "/star", "/own") == [True, False]


def test_robots_txt_itself_is_always_allowed() -> None:
    """robots.txt itself is always allowed."""
    rules = _rules("User-agent: *\nDisallow: /")

    assert _verdicts(rules, "/robots.txt", "/robots.txt?x=1", "/other") == [True, True, False]


def test_a_rule_line_before_any_user_agent_is_ignored() -> None:
    """a Disallow before any User-agent line belongs to no group."""
    assert _rules("Disallow: /\nUser-agent: *\nDisallow: /x\n").allowed(f"{HOST}/y") is True


NOISY = """\
# robots.txt captured 2026-10-28
﻿User-agent: *   # everyone
Crawl-delay: 10
Sitemap: https://site.example/sitemap.xml
this line has no colon
: value without a field
Dissallow: /typo
Disallow: /private   # trailing comment

Allow: /private/open
"""


def test_comments_blank_lines_unknown_fields_and_bad_lines_are_ignored_and_never_raise() -> None:
    """comments, blank lines, unknown fields and bad lines are ignored and never raise."""
    rules = _rules(NOISY)

    assert _verdicts(rules, "/private/x", "/private/open/x", "/typo", "/") == [False, True, True, True]


@pytest.mark.parametrize("text", ["", "\n\n", "#", ":", "::::", "User-agent", "User-agent:\nDisallow: /x", "\x00\x01"])
def test_degenerate_input_yields_rules_that_allow_everything(text: str) -> None:
    """degenerate input never raises and blocks nothing."""
    assert _rules(text).allowed(f"{HOST}/x") is True


def test_the_verdict_does_not_depend_on_rule_order() -> None:
    """the verdict does not depend on rule order, over shuffled rule lists."""
    rules = ["Disallow: /", "Allow: /a", "Disallow: /a/b", "Allow: /a/b/c", "Disallow: /*.pdf$", "Allow: /a/b/c"]
    paths = ["/", "/a", "/a/b", "/a/b/c", "/a/b/c/d.pdf", "/z", "/x.pdf"]
    expected = _verdicts(_rules("User-agent: *\n" + "\n".join(rules)), *paths)

    for seed in range(25):
        shuffled = random.Random(seed).sample(rules, len(rules))
        assert _verdicts(_rules("User-agent: *\n" + "\n".join(shuffled)), *paths) == expected
