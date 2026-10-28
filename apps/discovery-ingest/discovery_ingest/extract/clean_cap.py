"""Character cap of the page cleaner: priority sections first, whole lines only."""

from __future__ import annotations

from discovery_ingest.extract.clean_rank import Section, is_heading, section_keys


def _length(lines: list[str]) -> int:
    return len("\n".join(lines))


def split_sections(lines: list[str]) -> list[Section]:
    """Group ``lines`` into sections, each starting at a heading line (text before the first heading is one)."""
    sections: list[Section] = []
    for line in lines:
        if is_heading(line) or not sections:
            sections.append([])
        sections[-1].append(line)
    return sections


def _rank_order(sections: list[Section], preferred: range | None) -> list[int]:
    """Section indices best first: main content, then prose, then priority headings; each group keeps document order."""
    keys = section_keys(sections, preferred)
    return sorted(range(len(sections)), key=keys.__getitem__)


def _leading_fit(lines: Section, budget: int) -> Section:
    """Return the longest prefix of ``lines`` whose lines, each counted with its newline, fit in ``budget``."""
    taken: Section = []
    for line in lines:
        budget -= len(line) + 1
        if budget < 0:
            break
        taken.append(line)
    return taken


def _budgeted(sections: list[Section], max_chars: int, preferred: range | None) -> dict[int, Section]:
    kept: dict[int, Section] = {}
    budget = max_chars + 1
    for index in _rank_order(sections, preferred):
        taken = _leading_fit(sections[index], budget)
        if taken:
            kept[index] = taken
            budget -= _length(taken) + 1
        if len(taken) < len(sections[index]):
            break
    return kept


def cap_lines(lines: list[str], max_chars: int, preferred: range | None = None) -> tuple[list[str], bool]:
    """Return ``lines`` within ``max_chars`` joined by newlines, and whether anything was left out.

    ``preferred`` is the range of ``lines`` that come from the main region; its sections are kept first.
    """
    if _length(lines) <= max_chars:
        return lines, False
    kept = _budgeted(split_sections(lines), max_chars, preferred)
    return [line for index in sorted(kept) for line in kept[index]], True
