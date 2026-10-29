---
name: "Chapter E18 — Non-documents and tag restraint"
overview: "Teach the prompt that devices, apps, categories of works, generic form words, leaflets and lists of authorities are not documents, and that domain and life-situation codes are given only for a procedure the page clearly describes; add deterministic guards where the recorded ext-4 answers justify them."
todos:
  - id: prompt
    content: "Prompt rules for non-documents and for conservative codes; PROMPT_VERSION ext-5"
    status: pending
  - id: guards
    content: "Name guard for generic one-word or device names and a code guard for pages with no documents, only if the recorded answers justify them"
    status: pending
isProject: false
---

# Chapter E18 — Non-documents and tag restraint

**Repo:** `redtape` (`apps/discovery-ingest`) · **Branch:** `feat/extraction-non-documents` · **Status:** planned

**Depends on:** [E3](03-extraction-schema-and-grounding.md), [E15](15-quote-shape.md), [E16](16-documents-not-data-fields.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/extraction`

**Order:** executes after [E8](08-admin-display.md), before [E9](09-docs-and-operator-steps.md). Owner decision 2026-10-29: get as close as possible to the X16 thresholds and accept what comes.

## Goal

The live eval of 2026-10-29 under `ext-4` (all 20 gold pages, production taxonomy) gave:

| Model | Precision (0.80) | Recall (0.60) | Grounded (0.95) | Tag agreement (0.60) | Neurons per page |
| --- | --- | --- | --- | --- | --- |
| `qwen3-30b-a3b-fp8` | 0.53 | 0.79 | 0.87 | 0.49 | 65 |
| `llama-3.3-70b-instruct-fp8-fast` | 0.57 | 0.51 | 0.59 | 0.71 | 154 |

(Mistral Small 3.1 stopped on the daily quota after 7 pages; Scout did not run. Both rerun after the quota resets.) Qwen's quote grounding is clean (no `quote` drops); its grounded rate is lowered by `data_field` and `duplicate` drops. Two kinds of error remain, seen in the recorded Qwen answers:

1. **Things that are not documents** are reported as documents: devices and software (`Kartenlesegerät`, `Smartphone`, `AusweisApp2`, `digitales Erfassungsgerät`), categories of works (`Filmwerke`, `Spiele`, `Schriftwerke`, `Tonwerke`, `Multimediawerke`, `Sonstige`), generic words (`PDF-Formular`, `Online-Formular`, `Antragsformularen`, `Bestätigung`, `Bekanntmachung`), information sheets and lists of authorities (`Merkblatt …`, `Informationen und Ausfüllhinweise …`, `Behördenliste - …`, `Datenschutzhinweise`). The gold README already excludes leaflets, guides and checklists.
2. **Codes are invented** on pages that are not a procedure: `ble-kaese-lagerhaltung` (gold: other) got `housing`, `moving-house`, `vehicles-mobility`; `fragebogen-bundeskartellamt-registrierung` got `new-job`, `starting-school`, `vehicles-mobility`; `aa-transferkurzarbeitergeld` got `retirement`, `social-benefits`. This holds tag agreement at 0.49.

## Contract

1. **Prompt (`PROMPT_VERSION` `ext-5`).** Two additions to the system message, short, in the register of the existing rules, no examples unless the rule alone is shown too weak:
   - A document is a specific named paper or file. A device, an app or software, a category or type of work, a generic word (`Formular`, `Bestätigung`, `Antrag` without a specific title), an information sheet or leaflet (`Merkblatt`, `Hinweise`, `Informationen`), a list of authorities and a data-protection notice are not documents; report none of them.
   - Give a domain or life-situation code only for a procedure the page clearly describes, at most three of each, and none when the page is not a procedure (a start page, a list, a login page, a general information page). When unsure give none.
   `extractor_version()` stays within 32 characters; the wording digest pin is updated.
2. **Guards (only if the recorded answers justify them; measure first).**
   - *Name guard:* extend the `NAME_REJECTIONS` of E16 (in `ground_rules.py`) with a named tuple of patterns for names that are a generic word alone (`PDF-Formular`, `Online-Formular`, `Antragsformularen`, `Bestätigung`, `Bekanntmachung`, `Sonstige`) and names that begin with `Behördenliste`, `Datenschutz`. Drop reason `generic_name`. It must remove no gold document name (check all 47) and no name of a `required`/`form`/`issued` item that the gold set labels.
   - *Code guard:* a page whose page kind is not `service`, or which kept no documents, carries no domain or situation codes. Measure on the recorded answers first: how many predicted codes it removes and how many gold codes it would lose (the gold pages with codes and no documents are `bfj-gewerbezentralregister`; accept that loss only if the net tag agreement rises).
   - A guard that fails its measurement is not built; say so in the return.
3. **Grounding, cleaner, schema and gold labels unchanged.** No `.gold.json` is edited.

## TDD loops

### Loop A — Prompt

**Red** (`test_extraction_prompt.py`)

1. `the system message says that devices, apps, categories of works, generic words, leaflets and lists of authorities are not documents`.
2. `the system message limits codes to a procedure the page clearly describes, at most three of each`.
3. `earlier rules are kept: one quote per line (ext-3) and data fields are not documents (ext-4)` (negative: no rule lost).
4. `the wording digest test fails until PROMPT_VERSION is bumped and the digest for ext-5 is pinned`.
5. `extractor_version stays within 32 characters`.

**Green:** wording in `prompt_template.py`, version bump. **Refactor:** audit `prompt_template.py`; if the template is over the file guideline, split the rules block by concern.

### Loop B — Guards (conditional)

**Red** (`test_ground_generic_names.py`, `test_mapping_code_guard.py`)

1. `a generic name alone is dropped with the reason generic_name; a specific name that contains the word is kept` (`Antragsformular Grundstückskauf` kept).
2. `no gold document name on the committed gold set is dropped by the name guard` (all 47).
3. `a page of kind other, or with no kept documents, yields no codes; a service page with documents keeps its codes` (only if the code guard is built).
4. `Diagnostics counts generic_name drops`.

**Green:** one tuple of patterns and one filter each. **Refactor:** `ground_rules.py` is 119 lines after E16; split the name rejections into their own module if the file grows.

## Verification

```bash
cd apps/discovery-ingest && python -m pytest && ruff check . && ruff format --check . && mypy discovery_ingest
```

Offline measurement (no model call, no neurons) for the return, over the recorded `ext-4` answers of the 2026-10-29 eval. They sit in a read-only cache at `/tmp/claude-364864/-home-schult-v-projects-redtape/a8f7f06f-d1fb-4ebe-bcb3-5162ffff518b/scratchpad/evalcache` (keyed by model, prompt version, clean version, taxonomy digest, page name and text digest; per-page results in `scratchpad/evalruns/qwen.json` and `llama70b.json`). Use a copy; do not write into it. Report per guard: items or codes removed, gold names or codes lost, and the recomputed precision and tag agreement for both models. The prompt's effect cannot be measured offline: the chief of staff re-runs `llm eval` after the daily quota resets.

## Out of scope

A model change, fuzzy name matching, editing gold labels, segment-wise grounding, a second model call, running `llm eval`.
