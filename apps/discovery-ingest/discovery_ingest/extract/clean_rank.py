"""Section ranking of the page cleaner under the cap: main content first, menus last, priority headings first."""

from __future__ import annotations

import re
from itertools import accumulate, groupby

Section = list[str]
RankKey = tuple[bool, bool, bool]

PRIORITY_WORDS = (
    "unterlagen",
    "nachweis",
    "voraussetzung",
    "formular",
    "erforderlich",
    "mitbring",
    "antrag",
    "dokument",
)
MENU_MIN_LINKS = 11
SENTENCE_MIN_WORDS = 4

_PRIORITY_HEADING = re.compile(rf"#{{1,6}} .*(?:{'|'.join(PRIORITY_WORDS)})", re.IGNORECASE)
_HEADING = re.compile(r"#{1,6} ")
_LINK_TARGET = re.compile(r"\(https?://[^)\s]*\)")
_FILE_INFO = re.compile(r"\([A-Za-z]{2,5}, [\d.,]+ [KMG]B")
_SENTENCE_END = (".", "!", "?", ";", ",")


def is_heading(line: str) -> bool:
    """Return whether ``line`` is a markdown heading."""
    return _HEADING.match(line) is not None


def _is_bullet(line: str) -> bool:
    return line.startswith("- ")


def _lacks_sentence(line: str, text: str) -> bool:
    """Return whether a bullet is no sentence (it does not end like one) or a plain line has under four words."""
    return not text.endswith(_SENTENCE_END) if _is_bullet(line) else len(text.split()) < SENTENCE_MIN_WORDS


def _is_bare(line: str) -> bool:
    """Return whether a line is bare: a heading, a bullet that is no sentence, or a label of fewer than four words.

    A line that carries a file size (``(PDF, 105 KB``) names a document to download, so it is content.
    """
    text = _LINK_TARGET.sub("", line).strip()
    return is_heading(line) or (not _FILE_INFO.search(text) and _lacks_sentence(line, text))


def _is_link_item(line: str) -> bool:
    return _is_bullet(line) and _LINK_TARGET.search(line) is not None


def _menu_flags(lines: Section) -> list[bool]:
    """Flag every line that sits in a run of bare lines holding more than ten link items."""
    flags: list[bool] = []
    for bare, run in groupby(lines, key=_is_bare):
        run_lines = list(run)
        is_menu = bare and sum(map(_is_link_item, run_lines)) >= MENU_MIN_LINKS
        flags.extend([is_menu] * len(run_lines))
    return flags


def span_of(lines: Section, inner: Section) -> range | None:
    """Return where ``inner`` sits as a consecutive run inside ``lines``, or ``None`` when it does not."""
    width = len(inner)
    for start in range(len(lines) - width + 1):
        if width and lines[start] == inner[0] and lines[start : start + width] == inner:
            return range(start, start + width)
    return None


def _is_priority(section: Section) -> bool:
    return _PRIORITY_HEADING.match(section[0]) is not None


def _is_outside(start: int, preferred: range | None) -> bool:
    return preferred is not None and start not in preferred


def section_keys(sections: list[Section], preferred: range | None) -> list[RankKey]:
    """Return the sort key of each section: (outside the main region, only a menu, not a priority heading).

    ``False`` sorts first, so main content comes before the rest, prose before menus, priority headings before others.
    """
    flags = _menu_flags([line for section in sections for line in section])
    starts = list(accumulate((len(section) for section in sections), initial=0))
    return [
        (_is_outside(start, preferred), all(flags[start:end]), not _is_priority(section))
        for section, start, end in zip(sections, starts, starts[1:], strict=False)
    ]
