---
name: "Chapter 5 — Document-level classification eval"
overview: "Add an eval path that classifies a gold document's own text directly, to test (not assume) whether per-document classification beats the page-level baseline on the situation axis."
todos:
  - id: fixture-gap
    content: "Add an optional document_text field to GoldDocument and hand-author it for a small subset of the 47 gold documents"
    status: pending
  - id: document-case
    content: "Build DocumentCase from a GoldPage + GoldDocument pair that has document_text set, skipping the rest"
    status: pending
  - id: runner-path
    content: "Add EvalRunner.run_documents, wrapping document_text in a synthetic CleanPage so build_messages/_key/ground run unmodified"
    status: pending
  - id: scoring
    content: "Score document-level runs with chapter 1's situation-axis tag_agreement split, against the same documents' page-level baseline"
    status: pending
  - id: tests
    content: "Add tests proving the mechanism works on fixtures and never fakes a score when document_text is missing"
    status: pending
isProject: false
---

# Chapter 5 — Document-level classification eval

**Repo:** `redtape` (`apps/discovery-ingest`) · **Branch:** `feat/situation-tag-coverage-document-level-classification-eval` · **Status:** planned

**Depends on:** Chapter 1 ([01-split-tag-agreement-by-axis.md](01-split-tag-agreement-by-axis.md)) · **Decisions:** extraction X8 (why page-level consensus is the baseline being compared against); this suite's working hypothesis (cite `../gaps-and-decisions.md`) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-situation-tag-coverage`

## Goal

Extend the eval runner so it can optionally score the existing extractor/classification logic against a **document's own text** instead of its procedure page, for the subset of the 47 gold documents where that's feasible, producing a situation-axis tag-agreement number directly comparable — via chapter 1's split metric — to the page-level baseline. This tests the user's original idea ("comb through all the documents and extract chips directly") against the working hypothesis that it underperforms, because most gold documents are generic bureaucratic forms ("Antrag auf …") whose own text carries no life-situation signal in isolation — the signal lives in the surrounding procedure narrative (extraction X8: `.plans/extraction/gaps-and-decisions.md:22`), not the form text itself.

## Design

**The data gap (confirmed by reading the fixtures, not assumed).** `apps/discovery-ingest/tests/fixtures/gold/README.md:3-5,47` describes the gold set as 20 `<name>.html` page snapshots with `<name>.gold.json` labels, holding 47 documents and 2 edges in total. `GoldDocument` (`apps/discovery-ingest/discovery_ingest/extract/llm/evaluation/gold.py:25-32`) is:

```python
class GoldDocument(_Strict):
    name: Name
    role: Role
    condition: str | None = None
    is_optional: bool = False
```

There is no `url`, no `quote`, and no standalone text for any of the 47 — a document is a *name* inside a page's label file, not a text blob. `GoldPage.html` (`gold.py:41-51`) is the one page's HTML; nothing else is checked in per document. So today, **per-document text does not exist for any of the 47 gold documents** — this chapter must add it for a subset, not merely wire a code path to data that already exists.

**Why a procedure-page quote won't do.** The obvious shortcut — lift the sentence that names the document out of its procedure page — would still carry the procedure's narrative framing, which is exactly the signal this experiment is trying to isolate the document *from*. Scoring that as "document-level" would quietly re-test the page-level baseline under a new name. So `document_text` must be the document's own text (e.g. a linked form's own title/instructions, or a PDF's own cover text), not an excerpt of the page that mentions it.

**Fixture fix, sized small.** Add `document_text: str | None = None` to `GoldDocument` (`gold.py:25-32`); `_Strict`'s `extra="forbid"` means every other gold label keeps validating unchanged with the field simply absent. Hand-author `document_text` for a small, explicitly bounded subset — on the order of 5–10 of the 47, across 2–4 pages, picked for having a realistically recoverable standalone text (e.g. `bzkj-antrag-indizierung`'s one `form`-role document, or one of `aa-ferienbeschaeftigung`'s eight documents if its linked form is still fetchable) — not all 47, and not a general scraping pipeline. If, on inspection, none of the linked documents are still fetchable from their original source, the fallback is a short, honestly-labelled hand-transcription of what that document type's own front matter typically says (its own title and purpose line), clearly distinguishable in review from the procedure's prose. This authoring step is a prerequisite micro-step of this chapter, not a separate chapter.

**New code path, reusing existing machinery:**

- `DocumentCase` (new, `evaluation/gold.py` or a small sibling module): built from a `(GoldPage, GoldDocument)` pair where `document.document_text is not None`; carries `page_name`, `document_name`, `document_text`, and the gold axis label to score against — which is the **page's own** `situation_codes` (`GoldPage.situation_codes`, `gold.py:51`), since that is the one gold label this repo has for a document today (production itself copies the page's codes onto every document it mentions, per X8). A function `document_cases(pages: Sequence[GoldPage]) -> list[DocumentCase]` filters to the labelled subset; pages/documents without `document_text` are simply absent from the result, not silently scored.
- `EvalRunner.run_documents(cases: Sequence[DocumentCase]) -> EvalRun` (new method alongside `run`, `runner.py:46-54`): mirrors `_page` (`runner.py:60-71`) but builds a synthetic `CleanPage(text=case.document_text, links=frozenset(), language=None, title=None, truncated=False, version="doc-gold-1")` instead of calling `clean_page(gold.html, ...)` (`runner.py:61`). Everything downstream — `build_messages` (`prompt.py:32-35`, which only reads `clean_page.text`), `_cached_or_ask`/`_ask`/`_key` (`runner.py:73-100`), `_parse`, and `ground()` (`ground.py:34-43`) — runs unmodified against this synthetic page, so no parallel prompt or client plumbing is needed.
- `_key` (`runner.py:84-89`) already parameterises the cache by `page.cleaned.version` and `page.gold.name`; passing `version="doc-gold-1"` and `name=f"{page_name}::{document_name}"` keeps document-level cache entries (`cache.py:15-29`) from colliding with page-level ones under the existing `ResultCache` convention — no new cache format.
- **Known, deliberate consequence of reusing `ground()` unmodified:** `_codes` (`ground.py:24-31`) returns `(), ()` whenever `documents` came back empty — "a page that kept no document carries none" (`ground.py:27`). Fed a single document's own text, the model will often ground zero sub-documents from it, which empties the predicted codes regardless of what the model said. This is not a bug to route around: an all-empty predicted-codes result is itself evidence for (or against) the working hypothesis, and routing around it (e.g. scoring raw ungrounded `extraction.situation_codes` instead) would stop comparing like with like against the page-level baseline, which is also scored on grounded codes (`scoring.py:52` — `grounded.domain_codes`/`grounded.situation_codes`).

**Scoring.** For each `DocumentCase`, pair `(grounded.situation_codes, case.gold_situation_codes)` and feed the pairs into chapter 1's situation-axis split of `tag_agreement` (today `tag_agreement` at `metrics.py:81-83` mixes both axes via `gold_codes` at `scoring.py:14-16`; chapter 1 is what separates it). Run the identical split metric over the **page-level** baseline restricted to just the pages that contributed a `DocumentCase`, so the two numbers this chapter produces are comparable on the same page subset, not confounded by the document-level run covering fewer pages than the full 20.

## Tests

New file `apps/discovery-ingest/tests/test_llm_eval_document_level.py` (or extend `test_llm_eval_gold_set.py` if that's where page-level eval tests already live):

- `test_document_cases_skip_documents_without_document_text` — build `document_cases` from a small fixture set where only some `GoldDocument`s carry `document_text`; assert the result excludes the rest, and that the count is exactly the labelled ones (not silently all 47).
- `test_document_cases_is_empty_when_no_gold_document_has_text` — a gold set with `document_text` unset everywhere returns `[]`, not a crash and not a fallback to page-level cases.
- `test_run_documents_scores_the_situation_axis_with_the_split_metric` — run `EvalRunner.run_documents` against a cached/stubbed client for 2-3 `DocumentCase`s; assert the resulting situation-axis `tag_agreement` (via chapter 1's split function) is computed from the document-level grounded codes, not the page-level ones.
- `test_run_documents_does_not_fall_back_to_page_text` — assert the messages sent to the (stub) client contain the document's own text and not the full page's cleaned text, for a case where the two differ; this is the test that would fail if a future refactor accidentally wires `run_documents` back to `clean_page(gold.html, ...)`.
- `test_document_level_cache_key_does_not_collide_with_the_page_level_key` — same gold page, run once through `run` and once through `run_documents`; assert the two `_key` results (or their `filename()`s) differ.

Running this against every feasible gold document and comparing the resulting number to the page-level baseline is this suite's live run LR5 — explicitly **not** part of this chapter's test gate, which only has to prove the mechanism works on a small fixture subset.

## Verification

```bash
cd apps/discovery-ingest && ./ci.sh
```

## Refactor gate

Once `run` and `run_documents` both exist, check whether their bodies duplicate more than the one line that differs (how the `CleanPage` is built) — if so, factor the shared body into a private helper taking a `CleanPage` + a gold-code pair, called by both `_page` and the document-level equivalent, rather than letting the duplication stand.

## Commits

- `feat(discovery-ingest): add an optional document_text field to gold document fixtures`
- `feat(discovery-ingest): hand-author document_text for a small gold-document subset`
- `feat(discovery-ingest): score classification against a document's own text via EvalRunner.run_documents`

## Out of scope

Running the live comparison and recording the verdict (LR5); building a general-purpose document-text extraction pipeline (PDF OCR, fetching arbitrary linked forms, etc.) beyond hand-authoring a small fixture subset; changing production behavior to classify documents instead of pages (that's only a future chapter if LR5's numbers justify it, which the working hypothesis predicts they won't).
