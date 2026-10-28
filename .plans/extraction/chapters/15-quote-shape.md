---
name: "Chapter E15 — Quote shape"
overview: "Stop the model from joining list items into one quote and stop the cleaner from printing screen-reader labels as page text: a prompt rule to quote a single line, and a cleaner rule that drops visually hidden helper text. Grounding stays strict."
todos:
  - id: srcleaner
    content: "Cleaner drops screen-reader-only and visually hidden helper text; CLEAN_VERSION clean-4"
    status: pending
  - id: prompt
    content: "Prompt rule: one line or bullet per quote, never a join; PROMPT_VERSION ext-3"
    status: pending
isProject: false
---

# Chapter E15 — Quote shape

**Repo:** `redtape` (`apps/discovery-ingest`) · **Branch:** `feat/extraction-quote-shape` · **Status:** planned

**Depends on:** [E2](02-page-cleaner.md), [E3](03-extraction-schema-and-grounding.md), [E12](12-extraction-quality-tuning.md), [E13](13-grounding-normalisation.md), [E14](14-raise-the-input-cap.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/extraction`

**Order:** executes after [E14](14-raise-the-input-cap.md) and before [E7](07-wiring-and-workflow.md). Owner decision 2026-10-28, from E13's findings: fix the prompt and the cleaner first; segment-wise grounding stays a fallback.

## Goal

After E13, 20 of 62 raw items on the recorded answers of the first live eval were still dropped. Twelve are quotes that join a heading to a later bullet (`Halten Sie bitte folgende Dokumente als Datei bereit: - positiv:Anschrift ...`, with two bullets between that the model skipped): the words are on the page but not as one contiguous run, so the strict rule of invariant 8 rejects them, rightly. The better fix is upstream: ask for one line per quote, and stop feeding the model noise that invites copying. The cleaner keeps `<span class="sr-only">positiv:</span>` from `ul.ba-list-positive` on arbeitsagentur.de, so every bullet reads `- positiv:Kundennummer`, and prints `Wichtig:Wichtig:` twice from a visible label plus its screen-reader copy. Both are cleaner artifacts.

## Contract

1. **Cleaner (`CLEAN_VERSION` `clean-4`).** Elements that are visually hidden helper text are dropped with their content: class tokens `sr-only`, `visually-hidden`, `visuallyhidden`, `screen-reader-text`, `show-for-sr`, `u-sr-only`, and the `hidden`/`aria-hidden` rules that already exist. The class list is one small named tuple, matched on whole class tokens (never a substring), and never applied to `html`, `body` or an element that contains the page's main content. A page without such spans is unchanged. The `positiv:` prefix and the doubled `Wichtig:` disappear at the source.
2. **Prompt (`PROMPT_VERSION` `ext-3`).** The system message says: a quote is one line or one list item copied exactly from the page; never join a heading and an item or two items into one quote; when a requirement lists several items, report each as its own document with its own quote. `extractor_version()` stays within 32 characters; the wording digest pin is updated.
3. **Grounding unchanged.** The contiguous-run rule of E13 stays. Segment-wise grounding is not built here; the decision is revisited from the live eval.
4. **Gold set.** No `.gold.json` is edited (under owner review). The gold manifest `cleaned_sha256` of pages whose cleaned text changes is updated only where a test requires it, and `cleaner_recall` must not fall (47 of 47 after E14).

## TDD loops

### Loop A — Hidden helper text

**Red** (`test_clean_page.py`, `test_clean_page_fixtures.py`)

1. `a span with class sr-only is dropped with its text`.
2. `a doubled label (visible text plus a screen-reader copy) is printed once`.
3. `a visible element whose id or text merely contains sr-only is kept` (negative: whole class tokens only).
4. `the page body and the main region are never dropped by this rule` (negative).
5. `cleaner_recall on the gold set does not fall` and `the committed arbeitsagentur gold pages no longer contain the positiv: label`.

**Green:** one tuple of class tokens and one filter in `clean_dom`. **Refactor:** audit `clean_dom.py` against the refactor gate.

### Loop B — Prompt

**Red** (`test_extraction_prompt.py`)

1. `the system message tells the model to quote one line or list item and never to join items`.
2. `the wording digest test fails until PROMPT_VERSION is bumped and the digest for ext-3 is pinned` (existing mechanism).
3. `extractor_version stays within 32 characters`.

**Green:** wording in `prompt_template.py`, version bump. **Refactor:** none expected.

## Verification

```bash
cd apps/discovery-ingest && python -m pytest && ruff check . && mypy discovery_ingest
```

Offline measurement for the return: over the 77 real pages (read-only pool), how many pages change under `clean-4`, the characters removed per host, and a check that no gold document name disappears from the cleaned text. The prompt's effect cannot be measured offline: the chief of staff re-runs `llm eval` afterwards (every page is a cache miss).

## Out of scope

Segment-wise grounding, fuzzy matching, editing gold labels, a model change, a second model call to repair quotes.
