"""A tiny gold set, a fake model and the wiring the ``llm eval`` command tests share."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from discovery_ingest.extract.llm.client import LlmResult
from discovery_ingest.extract.llm.errors import LlmError

MODEL = "@cf/meta/llama-3.1-8b-instruct"
SOURCE = "https://portal.example/"
ALPHA_TEXT = "Bitte bringen Sie Ihren Reisepass und die Meldebescheinigung mit."
PAGES = {
    "alpha": f"<html lang='de'><body><main><h1>Wohnsitz anmelden</h1><p>{ALPHA_TEXT}</p></main></body></html>",
    "beta": "<html lang='de'><body><main><h1>Anmeldung</h1><p>Bitte melden Sie sich mit BundID an.</p></main></body></html>",
    "gamma": "<html lang='de'><body><main><h1>Willkommen</h1><p>Hier finden Sie Neuigkeiten.</p></main></body></html>",
    "shell": "<html lang='de'><body><div id='app'></div></body></html>",
}
LABELS: dict[str, dict[str, Any]] = {
    "alpha": {
        "page_kind": "service",
        "documents": [{"name": "Reisepass", "role": "required"}, {"name": "Meldebescheinigung", "role": "required"}],
        "category_codes": ["home-and-housing"],
    },
    "beta": {"page_kind": "login_or_error"},
    "gamma": {"page_kind": "other"},
    "shell": {"page_kind": "other"},
}
ANSWERS: dict[str, dict[str, Any]] = {
    "Reisepass": {
        "page_kind": "service",
        "category_codes": ["home-and-housing"],
        "documents": [
            {"name": "Reisepass", "role": "required", "quote": "Ihren Reisepass"},
            {"name": "Phantom", "role": "required", "quote": "this sentence is not on the page"},
        ],
        "dependencies": [],
    },
    "BundID": {
        "page_kind": "login_or_error",
        "category_codes": [],
        "documents": [],
        "dependencies": [],
    },
    "Neuigkeiten": {
        "page_kind": "other",
        "category_codes": [],
        "documents": [],
        "dependencies": [],
    },
}


def long_page_html(characters: int) -> str:
    """A page whose cleaned text is about ``characters`` long: numbered lines, one paragraph each."""
    lines = (
        f"Hinweis {number:05d}: Bitte reichen Sie die Unterlagen vollständig ein." for number in range(characters // 60)
    )
    return (
        "<html lang='de'><body><main><h1>Verfahren</h1>"
        + "".join(f"<p>{line}</p>" for line in lines)
        + "</main></body></html>"
    )


def write_long_gold(directory: Path, *, count: int, characters: int = 25_000) -> Path:
    """Write ``count`` gold pages of about ``characters`` cleaned characters, each with no labelled documents."""
    directory.mkdir(parents=True, exist_ok=True)
    for number in range(count):
        name = f"long-{number:02d}"
        (directory / f"{name}.html").write_text(long_page_html(characters), encoding="utf-8")
        labels = {"source_url": f"{SOURCE}{name}", "documents": [], "dependencies": [], "category_codes": []}
        labels |= {"page_kind": "other"}
        (directory / f"{name}.gold.json").write_text(json.dumps(labels), encoding="utf-8")
    return directory


def write_gold(directory: Path, *, names: Sequence[str] = tuple(PAGES)) -> Path:
    """Write the chosen tiny gold pages and their labels into ``directory`` and return it."""
    directory.mkdir(parents=True, exist_ok=True)
    for name in names:
        (directory / f"{name}.html").write_text(PAGES[name], encoding="utf-8")
        labels = {"source_url": f"{SOURCE}{name}", "documents": [], "dependencies": [], "category_codes": []}
        labels |= LABELS[name]
        (directory / f"{name}.gold.json").write_text(json.dumps(labels), encoding="utf-8")
    return directory


class FakeLlm:
    """Answers by a marker found in the user message; records every call; raises an answer that is an error."""

    def __init__(
        self,
        answers: Mapping[str, dict[str, Any] | str | LlmError] = ANSWERS,
        *,
        usage: tuple[int | None, int | None] = (1000, 200),
        model: str = MODEL,
    ) -> None:
        self.answers = answers
        self.usage = usage
        self.model = model
        self.calls: list[str] = []

    def extract(self, messages: Sequence[dict[str, str]], json_schema: dict[str, Any], *, max_tokens: int) -> LlmResult:
        """Return the canned answer for the page in ``messages`` or raise the canned error."""
        user = messages[-1]["content"]
        marker = next(marker for marker in self.answers if marker in user)
        self.calls.append(marker)
        answer = self.answers[marker]
        if isinstance(answer, LlmError):
            raise answer
        text = answer if isinstance(answer, str) else json.dumps(answer)
        return LlmResult(text, self.usage[0], self.usage[1], self.model)
