"""Document-level classification eval: score a document's own text, not its procedure page (chapter 5)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from discovery_ingest.extract.llm.client import LlmResult
from discovery_ingest.extract.llm.evaluation.cache import ResultCache
from discovery_ingest.extract.llm.evaluation.gold import GoldDocument, GoldPage, document_cases
from discovery_ingest.extract.llm.evaluation.runner import EvalRunner
from discovery_ingest.extract.llm.evaluation.setup import EvalSetup
from discovery_ingest.extract.llm.evaluation.summary import summarise
from discovery_ingest.extract.llm.meter import NeuronMeter
from discovery_ingest.extract.llm.prompt import PROMPT_VERSION

from eval_fakes import FakeLlm
from ledger_fakes import FakeLedger, guard_for
from llm_fakes import taxonomy

MODEL = "@cf/meta/llama-3.1-8b-instruct"
SOURCE = "https://portal.example/"


def _gold_page(
    name: str = "alpha",
    *,
    html: str = "<html lang='de'><body><main><h1>Verfahren</h1><p>Platzhaltertext.</p></main></body></html>",
    documents: tuple[GoldDocument, ...] = (),
    situation_codes: tuple[str, ...] = (),
) -> GoldPage:
    return GoldPage(
        name=name,
        html=html,
        source_url=f"{SOURCE}{name}",
        page_kind="service",
        documents=documents,
        dependencies=(),
        domain_codes=(),
        situation_codes=situation_codes,
    )


def _runner(monkeypatch: pytest.MonkeyPatch, llm: Any, cache_dir: Path) -> EvalRunner:
    meter = NeuronMeter(guard_for(monkeypatch, FakeLedger(remaining=1_000_000)), 1_000_000)
    setup = EvalSetup(MODEL, PROMPT_VERSION, taxonomy(), 2000, 30_000, 1_000_000)
    return EvalRunner(llm, meter, setup, ResultCache(cache_dir))


def test_document_cases_skip_documents_without_document_text() -> None:
    """document_cases · only the documents that carry document_text come back, the rest are simply absent."""
    page = _gold_page(
        documents=(
            GoldDocument(name="Formular X", role="form", document_text="Formular X: amtliches Formular."),
            GoldDocument(name="Anlage Y", role="required"),
        )
    )

    cases = document_cases([page])

    assert [case.document_name for case in cases] == ["Formular X"]
    assert cases[0].document_text == "Formular X: amtliches Formular."


def test_document_cases_is_empty_when_no_gold_document_has_text() -> None:
    """document_cases · a gold set with document_text unset everywhere returns an empty list, not a crash or a fallback."""
    page = _gold_page(documents=(GoldDocument(name="Anlage Y", role="required"),))

    assert document_cases([page]) == []


def test_run_documents_scores_the_situation_axis_with_the_split_metric(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """run_documents · situation tag agreement is computed from the document-level grounded codes, not the page's."""
    matching = _gold_page(
        name="beta1",
        documents=(
            GoldDocument(
                name="Formular X", role="form", document_text="Formular X: Antrag auf Ummeldung des Wohnsitzes."
            ),
        ),
        situation_codes=("moving-house",),
    )
    mismatching = _gold_page(
        name="beta2",
        documents=(
            GoldDocument(
                name="Formular Y", role="form", document_text="Formular Y: Antrag auf Geburtsanzeige des Kindes."
            ),
        ),
        situation_codes=("birth-of-child",),
    )
    cases = document_cases([matching, mismatching])
    answers = {
        "Formular X": {
            "page_kind": "form",
            "domain_codes": [],
            "situation_codes": ["moving-house"],
            "documents": [{"name": "Formular X", "role": "form", "quote": "Formular X"}],
            "dependencies": [],
        },
        "Formular Y": {
            "page_kind": "form",
            "domain_codes": [],
            "situation_codes": ["moving-house"],
            "documents": [{"name": "Formular Y", "role": "form", "quote": "Formular Y"}],
            "dependencies": [],
        },
    }
    runner = _runner(monkeypatch, FakeLlm(answers), tmp_path / "cache")

    run = runner.run_documents(cases)

    assert [page.scores.predicted_situation_codes for page in run.pages] == [("moving-house",), ("moving-house",)]
    assert [page.scores.gold_situation_codes for page in run.pages] == [("moving-house",), ("birth-of-child",)]
    assert summarise(run.pages).situation_tag_agreement == pytest.approx(0.5)


def test_run_documents_does_not_fall_back_to_page_text(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """run_documents · the model sees the document's own text only, never the full cleaned page (no silent fallback)."""
    page_only = "Diese Seite handelt von einem ganz anderen Vorgang mit vielen weiteren Dokumenten."
    doc_only = "Formular Z: Antrag auf Erteilung einer Bescheinigung."
    page = _gold_page(
        name="gamma",
        html=f"<html lang='de'><body><main><h1>Verfahren</h1><p>{page_only}</p></main></body></html>",
        documents=(GoldDocument(name="Formular Z", role="form", document_text=doc_only),),
        situation_codes=("moving-house",),
    )
    case = document_cases([page])[0]

    class RecordingLlm:
        def __init__(self) -> None:
            self.sent: list[str] = []

        def extract(self, messages: Any, json_schema: Any, *, max_tokens: int) -> LlmResult:
            self.sent.append(messages[-1]["content"])
            answer = {
                "page_kind": "form",
                "domain_codes": [],
                "situation_codes": [],
                "documents": [],
                "dependencies": [],
            }
            return LlmResult(json.dumps(answer), 100, 20, MODEL)

    llm = RecordingLlm()
    runner = _runner(monkeypatch, llm, tmp_path / "cache")

    runner.run_documents([case])

    assert len(llm.sent) == 1
    assert doc_only in llm.sent[0]
    assert page_only not in llm.sent[0]


def test_document_level_cache_key_does_not_collide_with_the_page_level_key(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """run_documents · the same gold page run through run and run_documents writes two cache entries, not one."""
    html = (
        "<html lang='de'><body><main><h1>Verfahren</h1><p>Formular X: amtlicher Hinweistext.</p></main></body></html>"
    )
    page = _gold_page(
        name="delta",
        html=html,
        documents=(GoldDocument(name="Formular X", role="form", document_text="Formular X: amtlicher Hinweistext."),),
        situation_codes=("moving-house",),
    )
    case = document_cases([page])[0]
    answer = {"page_kind": "form", "domain_codes": [], "situation_codes": [], "documents": [], "dependencies": []}
    llm = FakeLlm({"Formular X": answer})
    cache_dir = tmp_path / "cache"

    _runner(monkeypatch, llm, cache_dir).run([page])
    _runner(monkeypatch, llm, cache_dir).run_documents([case])

    assert llm.calls == ["Formular X", "Formular X"]
    assert len(list(cache_dir.glob("*.json"))) == 2
