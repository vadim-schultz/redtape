"""Character cap of the page cleaner: priority sections first, whole lines only."""

from __future__ import annotations

import re

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
_PRIORITY_HEADING = re.compile(rf"#{{1,6}} .*(?:{'|'.join(PRIORITY_WORDS)})", re.IGNORECASE)
_HEADING = re.compile(r"#{1,6} ")

Section = list[str]


def _length(lines: list[str]) -> int:
    return len("\n".join(lines))


def split_sections(lines: list[str]) -> list[Section]:
    """Group ``lines`` into sections, each starting at a heading line (text before the first heading is one)."""
    sections: list[Section] = []
    for line in lines:
        if _HEADING.match(line) or not sections:
            sections.append([])
        sections[-1].append(line)
    return sections


def _is_priority(section: Section) -> bool:
    return _PRIORITY_HEADING.match(section[0]) is not None


def _priority_order(sections: list[Section]) -> list[int]:
    """Section indices with priority sections first; each group keeps document order."""
    return sorted(range(len(sections)), key=lambda index: not _is_priority(sections[index]))


def _leading_fit(lines: Section, budget: int) -> Section:
    """Return the longest prefix of ``lines`` whose lines, each counted with its newline, fit in ``budget``."""
    taken: Section = []
    for line in lines:
        budget -= len(line) + 1
        if budget < 0:
            break
        taken.append(line)
    return taken


def _budgeted(sections: list[Section], max_chars: int) -> dict[int, Section]:
    kept: dict[int, Section] = {}
    budget = max_chars + 1
    for index in _priority_order(sections):
        taken = _leading_fit(sections[index], budget)
        if taken:
            kept[index] = taken
            budget -= _length(taken) + 1
        if len(taken) < len(sections[index]):
            break
    return kept


def cap_lines(lines: list[str], max_chars: int) -> tuple[list[str], bool]:
    """Return ``lines`` within ``max_chars`` joined by newlines, and whether anything was left out."""
    if _length(lines) <= max_chars:
        return lines, False
    kept = _budgeted(split_sections(lines), max_chars)
    return [line for index in sorted(kept) for line in kept[index]], True
