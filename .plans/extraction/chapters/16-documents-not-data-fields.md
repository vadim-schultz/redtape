---
name: "Chapter E16 — Documents, not data fields"
overview: "Teach the prompt that a document is something a person brings, sends or receives, never a data item such as an address, number or confirmation; bump PROMPT_VERSION to ext-4 and measure the effect on the recorded answers."
todos:
  - id: prompt
    content: "Prompt rule: data fields, identifiers and facts are not documents; PROMPT_VERSION ext-4"
    status: pending
  - id: guard
    content: "Optional cheap guard in mapping for obvious data-field names, only if the recorded answers justify it"
    status: pending
isProject: false
---

# Chapter E16 — Documents, not data fields

**Repo:** `redtape` (`apps/discovery-ingest`) · **Branch:** `feat/extraction-data-fields` · **Status:** planned

**Depends on:** [E3](03-extraction-schema-and-grounding.md), [E5](05-eval-harness-and-model-choice.md), [E15](15-quote-shape.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/extraction`

**Order:** executes after [E7](07-wiring-and-workflow.md), before [E17](17-price-rows-for-candidate-models.md). Owner decision 2026-10-29 (proposed in the session hand-off, approved by the owner).

## Goal

The name-versus-role check on the cached eval answers (E5, third eval) found that both models list **data fields as documents** on `aa-transferkurzarbeitergeld`: `Anschrift des personenabgebenden Betriebs`, `Betriebsnummer der Lohnabrechnungsstelle`, `Transferkurzarbeitergeld-Nummer`. These are items the applicant types into a form, not things they bring, send or receive. The gold labels already exclude them (`tests/fixtures/gold/README.md`: "Identifiers and data items are not documents"), so each one lowers precision. The prompt (`ext-3`) has no rule that says so.

## Contract

1. **Prompt (`PROMPT_VERSION` `ext-4`).** The system message says: a document is a paper or file a person brings, sends, fills in or receives (certificate, proof, form, notice, application, extract). An address, a number (customer, company, reference, tax, account), a date, a name of a person or body, a yes/no fact and a piece of information to be stated are data, not documents; do not report them. When a page lists data to enter into a form, report none of them. The rule stays in the same language and register as the other rules; the wording is one short paragraph. `extractor_version()` stays within 32 characters; the wording digest pin in `WORDING_DIGESTS` is updated.
2. **Few-shot or example text is not added** unless the rule alone proves too weak on the recorded answers (token cost).
3. **Guard (only if justified).** If the recorded answers show data-field names that a model still returns, a deterministic filter in `mapping` may drop names that are clearly identifiers (for example a name that begins with `Anschrift`, `Nummer`, `Betriebsnummer`, `Kundennummer`, or ends with `-Nummer`). It is added only with a measurement that it removes no gold document name, and it is a named tuple of patterns, not a model call. If no measurement justifies it, do not build it.
4. **Grounding, schema, cleaner and gold labels unchanged.** No `.gold.json` is edited.

## TDD loops

### Loop A — Prompt rule

**Red** (`test_extraction_prompt.py`)

1. `the system message says that addresses, numbers, dates and facts to state are not documents`.
2. `the system message still carries the one-line-per-quote rule of ext-3` (negative: no rule lost).
3. `the wording digest test fails until PROMPT_VERSION is bumped and the digest for ext-4 is pinned` (existing mechanism).
4. `extractor_version stays within 32 characters`.

**Green:** wording in `prompt_template.py`, version bump. **Refactor:** audit `prompt_template.py` and the wording tests against the refactor gate.

### Loop B — Guard (conditional)

Build only if the offline measurement below justifies it.

**Red** (`test_mapping_data_fields.py`)

1. `a name that is an identifier or address is dropped with the reason data_field`.
2. `no gold document name on the committed gold set is dropped by the guard` (negative, over all 47 gold names).
3. `Diagnostics counts the dropped data fields`.

**Green:** one tuple of patterns and one filter. **Refactor:** none expected.

## Verification

```bash
cd apps/discovery-ingest && python -m pytest && ruff check . && mypy discovery_ingest
```

Offline measurement for the return (no model call, no neurons): over the recorded answers in the eval caches (if the previous session's scratchpad caches are gone, say so and skip the measurement), list the names that look like data fields, how many a guard pattern set would remove, and that no gold name is among them. The prompt's effect cannot be measured offline: the chief of staff re-runs `llm eval` for the candidate models afterwards.

## Out of scope

A model change, fuzzy name matching, editing gold labels, segment-wise grounding, a second model call to filter names, running `llm eval` (the chief of staff does it).
