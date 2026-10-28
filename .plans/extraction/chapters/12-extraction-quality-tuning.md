---
name: "Chapter E12 — Extraction quality tuning"
overview: "Fix what the first live eval of llama-3.3-70b showed: a deterministic repair for percent-encoded model text, page-kind guidance in the prompt, cleaner defects that hide or merge document names, and the E4 probe and meter loose ends. Each fix is driven by a real failing answer and measured by a re-run of the gold set."
todos:
  - id: decode
    content: "Percent-decode repair of names, quotes and conditions before grounding"
    status: pending
  - id: prompt
    content: "Page-kind guidance and a prompt version bump"
    status: pending
  - id: cleaner
    content: "Space between a link title and its description; main content first under the cap"
    status: pending
  - id: probe
    content: "Probe row bugs, prompt-overhead estimate and settling on reported neurons"
    status: pending
isProject: false
---

# Chapter E12 — Extraction quality tuning

**Repo:** `redtape` (`apps/discovery-ingest`) · **Branch:** `feat/extraction-tuning` · **Status:** planned

**Depends on:** [E2](02-page-cleaner.md), [E3](03-extraction-schema-and-grounding.md), [E4](04-workers-ai-client-and-probe.md), [E5](05-eval-harness-and-model-choice.md) and its first live eval (see the [ledger](../run-ledger.md)) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/extraction`

**Order:** executes after [E6](06-llm-extract-handler.md) and before [E7](07-wiring-and-workflow.md). It changes grounding, the prompt and the cleaner only; the handler of E6 and the wiring of E7 do not depend on it. Owner decision 2026-10-28: tune now and review the gold labels in parallel.

## Goal

The first eval of `@cf/meta/llama-3.3-70b-instruct-fp8-fast` (prompt `ext-1`, clean-1, 20 gold pages) scored precision 0.30, recall 0.21, grounded rate 0.55 against targets of 0.80, 0.60 and 0.95. Of 62 raw items 28 were dropped (22 quote, 6 dependency endpoint). This chapter fixes the causes that are visible in the data, then re-runs the same gold set so the improvement is a number. The gold labels are provisional and under human review in parallel; no fix here edits them.

## Evidence (real answers, no new model calls)

The eval wrote its raw answers and results outside the repository; the owner supplies them as fixtures, or the chapter copies the few it needs into `tests/fixtures/llm_answers/` (names, quotes and page text only, redacted like the gold set):

- `aa-ferienbeschaeftigung`: the model emitted `Erkl%C3%A4rung zur Immatrikulationsbescheinigung` and quotes with `%E2%80%9D`; the cleaned text has none, so every such quote failed grounding.
- `ble-fleisch-intervention` (8 gold documents) and `bvl-tierarzneimittel-meldung` (2): answered `page_kind: other` with empty lists in 29 output tokens.
- `aa-ferienbeschaeftigung` gold name `Antragsformular Ferienbeschäftigung für ausländische Studierende, Fachschüler/innen`: absent from the cleaned text because a `strong` title and a block description inside one link are joined without a space.
- `ble-fleisch-intervention`: the cap kept the BLE menu and cut `Bestandsliste` (page text 21,238 characters, cap 12,000).

## Contract

1. **Percent repair (E3 grounding).** Before grounding, a name, quote or condition that contains `%XX` sequences is percent-decoded as UTF-8 when the result is valid and the string contains at least two sequences; anything else is left alone. The repair is one small function with its own diagnostics counter (`repaired`), applied once per item, never to URLs.
2. **Prompt.** The wording says a page is a `service` when it names documents, forms or evidence a person must bring or send, even inside a procedure description, and that `other` is only for pages with no such list. `PROMPT_VERSION` becomes `ext-2` and the digest pin is updated; `extractor_version` still fits 32 characters.
3. **Cleaner.** A link title and the text of a block inside the same link are separated by a space or newline. When the page text exceeds the cap, sections inside `main` (or the largest `article`) are kept before sections outside it, and menu-like blocks outside `nav` (a list of more than ten links with no sentence text) rank below prose. `CLEAN_VERSION` becomes `clean-2`.
4. **Probe and meter loose ends (E4).**
   - The probe's `violation` row must not report "not valid JSON" for an answer that parsed, and its `cost` row must read the usage the client returned.
   - `PROMPT_OVERHEAD_TOKENS` falls to the measured value (about 400, with a test that pins the estimate against the recorded probe: 1,597 prompt tokens for a 3,694-character page).
   - When `result.usage.neurons` is present, `NeuronMeter.settle` uses it as the actual cost; the price table remains the estimate and the fallback.

## TDD loops

Every fix starts from a real failing item. Tests use the fake client and canned answers.

### Loop A — Percent repair

**Red** (`test_ground_repair.py`)

1. `a percent-encoded name and quote are decoded and then grounded against the cleaned text`.
2. `a string with fewer than two percent sequences or an invalid UTF-8 result is left unchanged and still fails grounding if it is not on the page`.
3. `urls are never decoded by the repair`.
4. `the repaired count is reported in the diagnostics`.

**Green:** one function applied in the grounding entry point. **Refactor:** the function is pure and under five lines.

### Loop B — Prompt

**Red** (`test_prompt.py`, `test_prompt_version.py`)

1. `the system message tells the model that a page listing documents to bring is a service even inside a procedure`.
2. `a wording change without a new prompt version still fails the digest test` (existing); the new digest is pinned for `ext-2`.

**Green:** wording in `prompt_template.py`, version bump. **Refactor:** none expected.

### Loop C — Cleaner

**Red** (`test_clean_page.py`, `test_clean_page_cap.py`, `test_clean_page_fixtures.py`)

1. `a link containing a strong title and a block description keeps a space between them`.
2. `under the cap, sections inside main are kept before sections outside it`.
3. `a long list of bare links outside nav ranks below prose under the cap`.
4. `the recall gate and the character ratio still pass on the committed fixtures`.
5. `cleaner_recall on the gold set does not fall`, and rises to at least 46 of 47 with the default cap (it was 44 of 47).

**Green/Refactor:** rules stay split by concern (`clean_cap`, `clean_markdown`).

### Loop D — Probe and meter

**Red** (`test_llm_probe.py`, `test_neuron_meter.py`, `test_llm_prices.py`)

1. `the violation row reports a usable answer as usable and an unparsable one as a finding`.
2. `the cost row uses the usage the client returned`.
3. `settle uses the reported neurons when present and the price table otherwise`.
4. `the estimate for the recorded probe page is within 15 percent of the 160 neurons the API reported`.

**Green/Refactor:** one small change per row; the price module keeps the formula in one place.

## Verification

```bash
cd apps/discovery-ingest && python -m pytest && ruff check . && mypy discovery_ingest
```

Live gate (the chief of staff runs it; spends neurons, the cache makes unchanged pages free): re-run `llm eval --model @cf/meta/llama-3.3-70b-instruct-fp8-fast` on the gold set with `ext-2` and `clean-2`, paste the table beside the first run in the ledger, and compare precision, recall, grounded rate, tag agreement and page-kind accuracy. Record `neurons_used` and the stored `llm_model` decision in X16.

## Out of scope

Changing the gold labels (owner review), switching model, multi-sample voting, a second repair call to the model, Trafilatura (decided from `cleaner_recall` after this chapter).
