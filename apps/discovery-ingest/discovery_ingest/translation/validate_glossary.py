"""The glossary validator: terms of the source must be rendered as required and kept terms must stay as written."""

from __future__ import annotations

import re
from typing import Final

from discovery_ingest.translation.findings import Check, Finding
from discovery_ingest.translation.glossary import Glossary

GLOSSARY_CHECK: Final = "glossary"


def _stem(word: str) -> str:
    """Cut an inflection ending off a word so that ``пособие`` and ``пособия`` meet."""
    if len(word) > 5:
        return word[:-2]
    return word[:-1] if len(word) > 3 else word


def _whole_word(term: str, text: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text) is not None


def _rendered(rendering: str, translated: str) -> bool:
    lowered = translated.casefold()
    words = [word.strip("()[]\"'.,;:") for word in rendering.casefold().split()]
    return all(_stem(word) in lowered for word in words if word)


def glossary_adherence(glossary: Glossary) -> Check:
    """Return the check that every glossary term of the source has its rendering and every kept term stays as written."""

    def check(source: str, translated: str) -> str | None:
        wrong = [
            e.source for e in glossary.terms if _whole_word(e.source, source) and not _rendered(e.rendering, translated)
        ]
        lost = [term for term in glossary.keep if _whole_word(term, source) and term not in translated]
        problems = [*(f"{term!r} not rendered as required" for term in wrong), *(f"{term!r} not kept" for term in lost)]
        return "; ".join(problems) or None

    return check


def glossary_findings(source: str, translated: str, glossary: Glossary) -> list[Finding]:
    """Return the adherence finding of one text, advisory when the glossary is in advisory mode; none when it adheres."""
    detail = glossary_adherence(glossary)(source, translated)
    return [Finding(GLOSSARY_CHECK, "text", detail, advisory=glossary.mode == "advisory")] if detail else []
