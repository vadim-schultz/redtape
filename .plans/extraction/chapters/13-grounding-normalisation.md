---
name: "Chapter E13 — Grounding normalisation"
overview: "Make quote grounding symmetric: strip list bullets and fold typographic quote marks in the quote and in the page text alike, so a model quote that spans a heading and a bullet, or uses different quote glyphs, still finds its place in the cleaned text. Invented quotes still fail."
todos:
  - id: bullets
    content: "Bullets and list markers inside a quote or inside a text line"
    status: pending
  - id: quotes
    content: "Fold typographic quote marks and dashes the same way on both sides"
    status: pending
  - id: regress
    content: "Recorded answers regress test with a negative case"
    status: pending
isProject: false
---

# Chapter E13 — Grounding normalisation

**Repo:** `redtape` (`apps/discovery-ingest`) · **Branch:** `feat/extraction-grounding-norm` · **Status:** planned

**Depends on:** [E3](03-extraction-schema-and-grounding.md), [E12](12-extraction-quality-tuning.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/extraction`

**Order:** executes after [E12](12-extraction-quality-tuning.md) and before [E7](07-wiring-and-workflow.md). Grounding only: no prompt, cleaner, schema or model change.

## Goal

E12 left 25 of 62 raw items dropped on the recorded answers of the first live eval. About 18 are quotes that span a heading line and a bullet (for example `Sie benötigen: - positiv:Kundennummer ...`, `aa-probebeschaeftigung` 7, `aa-transferkurzarbeitergeld` 11). `normalise()` strips a bullet only at the start of a line, so the quote's mid-text `- ` has no counterpart in the page text and the quote fails. Three more fail because the model wrote `%E2%80%9D` (right double quote) for both opening and closing marks while the page has „…“. These are grounding mismatches, not inventions: the words are on the page. This chapter makes both sides normalise the same way, so recall is no longer lost to glyphs. Invariant 8 stays: an item whose words are not on the page is still dropped.

## Contract

1. **One rule for both sides.** `normalise` is applied to the quote and to the cleaned text. It removes list bullets (`-`, `*`, `+`, `•`, `·` followed by a space) wherever they stand after whitespace or at a line start, and the labels the cleaner prints before an item text if the cleaner emits any (decide from evidence: the `positiv:` and `negativ:` prefixes in the recorded text; if they are cleaner artifacts of CSS class names, strip them in `normalise` and report so a later cleaner change can remove them at the source).
2. **Typographic folding.** Straight and curly single and double quotes (`" ' „ “ ” ‚ ‘ ’ « » ‹ ›`) are removed or mapped to one placeholder on both sides, and en and em dashes map to a hyphen that is then treated as a separator, so a model's `”` for `„` still matches.
3. **Unchanged:** the name slug (`name_slug`), the URL rules, the percent repair of E12, and the rule that the quote must be a contiguous run of the normalised text. A quote that drops letters (the model wrote `verfgbare` for `verfügbare`) still fails: no fuzzy matching.
4. **Cap and prompt untouched.** The one gold name lost to the cap (`Nachweis des Verwandtschaftsverhältnisses`) is a cap decision for the owner, not part of this chapter.

## TDD loops

Every test starts from a real failing item; canned answers are in `tests/fixtures/llm_answers/` (E12 added `aa-ferienbeschaeftigung.answer.json`; add the one or two small excerpts of the recorded answers this chapter needs, no personal data).

### Loop A — Bullets

**Red** (`test_extraction_normalise.py`, `test_ground_quotes.py`)

1. `a quote spanning a heading and a bullet grounds against the page text that has them on separate lines`.
2. `a bullet inside the page text is removed the same way`.
3. `a quote whose words are not on the page still fails even with bullets` (negative).
4. `a hyphen inside a word (Bundes-Agentur) is kept` (negative: the rule only touches a bullet followed by a space after whitespace).

**Green:** extend `normalise`. **Refactor:** the patterns are named constants, the function stays a few lines.

### Loop B — Quote marks

**Red**

1. `a quote written with a closing glyph where the page has an opening glyph still grounds`.
2. `dashes of different widths match each other`.
3. `a quote with different letters still fails` (negative: umlaut loss is not tolerated).

**Green/Refactor:** one translation table shared by both sides.

### Loop C — Recorded answers

**Red** (`test_ground_recorded_answers.py`)

1. `the recorded answers ground at least N more items than before this chapter` (N from the offline count; pin the new kept count) and `no item that was dropped for an invented quote becomes grounded` (negative: construct one from a recorded answer by changing one word).

**Green:** none beyond A and B. **Refactor:** audit `ground_rules.py` and `normalise.py` against the refactor gate.

## Verification

```bash
cd apps/discovery-ingest && python -m pytest && ruff check . && mypy discovery_ingest
```

Offline measurement for the return: over the 19 recorded answers, items kept and dropped before and after (current: 37 kept, 25 dropped, of 62 raw), by reason. The chief of staff re-runs the live eval afterwards; no model calls here.

## Out of scope

Fuzzy or edit-distance matching, raising the cleaner cap, prompt wording, editing gold labels.
