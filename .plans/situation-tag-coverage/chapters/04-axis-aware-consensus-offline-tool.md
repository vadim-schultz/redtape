---
name: "Chapter 4 — Axis-aware consensus offline tool"
overview: "An offline tool that re-runs the existing, already-parameterized aggregate_tags() against exported mention data under alternative situation-axis thresholds, to measure the coverage delta a relaxed threshold would buy before any production change."
todos:
  - id: variants
    content: "Add ThresholdVariant/VariantCoverage and situation_coverage_by_variant() as pure, DB-free logic"
    status: pending
  - id: cli
    content: "Add the measure_situation_tag_coverage CLI that loads an exported mentions JSON file and prints the table"
    status: pending
  - id: tests
    content: "Add the regression-guard and newly-covered-candidate tests against fixture mention data"
    status: pending
isProject: false
---

# Chapter 4 — Axis-aware consensus offline tool

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/situation-tag-coverage-axis-aware-consensus-tool` · **Status:** planned

**Depends on:** Chapter 1 ([01-split-tag-agreement-by-axis.md](01-split-tag-agreement-by-axis.md)) · **Decisions:** extraction X8; this suite's pending T-PENDING decision ([../gaps-and-decisions.md](../gaps-and-decisions.md)) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-situation-tag-coverage`

## Goal

Give whoever settles this suite's pending T-PENDING decision (`../gaps-and-decisions.md`) real numbers instead of a judgment call. `aggregate_tags()` already takes its thresholds as parameters (`apps/api/app/features/discovery/tags.py:44-48`, defaults `DEFAULT_MIN_PROCEDURES = 2` / `DEFAULT_MIN_SHARE = 0.5` at lines 10-11) — nothing needs to change in production code to try a different threshold on the situation axis. What is missing is a way to see, over real mention data, how many candidates that are untagged today would become tagged under a relaxed rule, split from the domain-axis numbers so the two don't get blended (the per-axis convention Chapter 1 establishes).

The root cause this suite exists to fix: `candidate_tags.py`'s `_consensus()` (`apps/api/app/features/discovery/candidate_tags.py:20-22`) calls `aggregate_tags` with `settings.discovery_tag_min_procedures` / `settings.discovery_tag_min_share` (`apps/api/app/config.py:93-100`, same defaults 2/0.5) for *both* axes via `_axis_support()` (`candidate_tags.py:25-27`), and `candidate_tag_suggestions()` (`candidate_tags.py:30-36`) applies that same pair of thresholds to `domain_codes` and `situation_codes` alike. Domains recur across many unrelated procedures and clear 2-procedure/50% easily; a life situation is by definition the one triggering event a single specific procedure handles, so it essentially never gets a second independent procedure's agreement. Live evidence from the 2026-10-29 drain (`.plans/extraction/run-ledger.md:65`): domain codes landed on 6 of 58 candidates, situation codes on 0 of 58. The one existing escape hatch, `curated_codes()` (`tags.py:61-71`), only fires when a human writes a `manual` mention (`MANUAL_EXTRACTOR`, `tags.py:12`) — it is not a substitute for a better extracted-consensus rule.

This chapter does **not** change `settings.discovery_tag_min_procedures`/`discovery_tag_min_share` or `candidate_tags.py`. It builds the measurement tool that produces the coverage table the decision needs: for each of 2-3 situation-axis threshold variants, how many candidates move from "no accepted situation code" to "accepted" — the coverage delta that is LR4's raw input.

## Design

**Where it lives.** `apps/api/scripts/` already holds this kind of offline, DB-free or DB-reading tool invoked as `python -m scripts.<name>` from `apps/api` (`apps/api/scripts/seed_taxonomy.py:1-5`; `apps/api/scripts/measure_code_rules.py`, an informational tool that prints a table and is tested directly by importing its pure functions in `apps/api/tests/test_measure_code_rules.py`). This chapter follows the same split `object_store_probe.py` / `object_store_probe_steps.py` already use — a thin CLI module plus a pure logic module — rather than putting measurement logic under `app/features/discovery/`, because this tool is not part of the production request path.

- **`apps/api/scripts/situation_tag_coverage_variants.py`** (new, pure, no DB/IO):
  - `ThresholdVariant(NamedTuple)`: `name: str`, `min_procedures: int`, `min_share: float`.
  - `BASELINE = ThresholdVariant("baseline (2 procedures, 50% share)", DEFAULT_MIN_PROCEDURES, DEFAULT_MIN_SHARE)` — imports the real defaults from `app.features.discovery.tags`, so a future change to those defaults cannot silently desync the tool's baseline from production.
  - `RELAXED_SINGLE_PROCEDURE = ThresholdVariant("relaxed (1 procedure, 50% share)", 1, DEFAULT_MIN_SHARE)` — the suite's headline proposal: trust one procedure's assertion for the situation axis.
  - `VariantCoverage(NamedTuple)`: `variant: str`, `accepted_candidates: int`, `newly_covered_candidates: int` (accepted under this variant but **not** under `BASELINE` — the actual coverage delta the decision needs, not just a raw count).
  - `situation_coverage_by_variant(candidates: Mapping[UUID, list[TaggedMention]], variants: Sequence[ThresholdVariant] = (BASELINE, RELAXED_SINGLE_PROCEDURE)) -> list[VariantCoverage]`: for each candidate's situation-axis mentions, calls `aggregate_tags(mentions, variant.min_procedures, variant.min_share)` (the real, unmodified function from `tags.py:44-58`) and counts the candidate as covered under a variant when any returned `TagSupport.accepted` is true. Computes the baseline-covered set once, then for every variant reports how many candidates are covered and how many of those are *new* relative to baseline.
  - `TaggedMention` and `DEFAULT_MIN_PROCEDURES`/`DEFAULT_MIN_SHARE` are imported directly from `app.features.discovery.tags` — no new mention type, no production code touched. This is the simplicity point worth stating plainly: the whole tool is new test/tool code sitting on top of an already-parameterized function; `tags.py` and `candidate_tags.py` are read-only dependencies of this chapter.

- **`apps/api/scripts/measure_situation_tag_coverage.py`** (new, thin CLI):
  - `main(argv: Sequence[str] | None = None) -> int`, invoked as `cd apps/api && python -m scripts.measure_situation_tag_coverage --input <export.json>`.
  - Reads a JSON export file: a flat list of records `{"candidate_id": "<uuid>", "catalogue_service_id": "<uuid>", "situation_codes": [...] | null}` — the same shape as the `(procedure_id, codes)` pairs `TaggedMention` already is, just JSON-serialized and grouped. `load_candidates(path: Path) -> dict[UUID, list[TaggedMention]]` groups records by `candidate_id` into the `Mapping` `situation_coverage_by_variant` expects.
  - Calls `situation_coverage_by_variant` and prints one row per variant (`format_table(results: Sequence[VariantCoverage]) -> str`, a pure function kept separate from `main` so it is unit-testable without a file on disk), mirroring the pass/fail table `measure_code_rules.py` and `object_store_probe.py` already print.
  - Producing the export JSON itself is a one-off read-only query against `discovery_candidate_mention` (`apps/api/app/models/discovery/discovery_candidate_mention.py:42,58-59` — `catalogue_service_id`, `domain_codes`, `situation_codes`), e.g. `SELECT candidate_id, catalogue_service_id, situation_codes FROM discovery_candidate_mention`, run by hand and saved to a file. This chapter does not add a reusable export endpoint or a new script for it — writing that query, running it against the real database, and feeding its output to `measure_situation_tag_coverage` is LR4's job, not this chapter's.

**The "grounded single page" variant is explicitly deferred, not scoped in.** It would need to know, per mention, something like whether the page's assertion was directly grounded in visible text versus inferred, or what kind of page it came from. `DiscoveryCandidateMention` (`apps/api/app/models/discovery/discovery_candidate_mention.py:21-64`) carries `role`, `excerpt`, `source_field`, `artifact_id`, `extractor`, `extractor_version`, `condition`, `is_optional`, `domain_codes`, `situation_codes` — no `page_kind` or grounding-confidence field exists on a mention today. Building this variant would require a schema extension (a new column plus whatever upstream extraction change populates it) that is out of scope for an offline measurement tool reading data that already exists. It is deferred to a later chapter, contingent on whether LR4's numbers for the two variants built here are inconclusive enough to justify adding that field.

## Tests

`apps/api/tests/test_situation_tag_coverage_variants.py` (fixture mention data, no DB — same style as `apps/api/tests/test_discovery_tags.py`'s `P1..P5` UUIDs):

- `test_baseline_variant_reproduces_aggregate_tags_two_and_fifty_percent` — build a `candidates` map with a mix of single-procedure and multi-procedure situation mentions; assert `situation_coverage_by_variant(candidates, (BASELINE,))[0].accepted_candidates` exactly equals the count obtained by calling `aggregate_tags(mentions, 2, 0.5)` directly per candidate and checking `any(s.accepted for s in ...)` — the regression guard pinning today's `aggregate_tags(mentions, 2, 0.5)` behavior.
- `test_relaxed_single_procedure_variant_covers_a_candidate_with_one_tagging_procedure` — a candidate whose situation code comes from exactly one procedure (today failing the 2-procedure bar, so absent from `BASELINE`'s covered set) is counted as `accepted_candidates` under `RELAXED_SINGLE_PROCEDURE` and contributes to `newly_covered_candidates`.
- `test_candidates_already_covered_by_baseline_are_not_counted_as_newly_covered` — a candidate with two procedures agreeing on a situation code is accepted under both `BASELINE` and `RELAXED_SINGLE_PROCEDURE`, so it must not inflate `newly_covered_candidates` for the relaxed variant.
- `test_candidate_with_two_situation_codes_from_one_procedure_counts_once` — a lone procedure's mention carrying two situation codes makes the candidate covered exactly once under `RELAXED_SINGLE_PROCEDURE`, not twice (guards against counting per-code instead of per-candidate).
- `test_candidate_with_no_situation_codes_is_covered_by_no_variant` — a candidate whose mentions carry only `domain_codes` (or `None`/`[]` situation codes) is absent from every variant's covered set.

`apps/api/tests/test_measure_situation_tag_coverage.py` (CLI, still no DB):

- `test_format_table_renders_one_row_per_variant_with_counts_and_delta` — given a fixed `list[VariantCoverage]`, assert the rendered string contains each variant's name, `accepted_candidates` and `newly_covered_candidates`.
- `test_load_candidates_groups_export_records_by_candidate_id` — a small JSON fixture file (`tmp_path`) with two records sharing one `candidate_id` groups into one `TaggedMention` list of length 2.
- `test_main_reads_an_export_file_and_prints_the_coverage_table` — write a fixture export JSON to `tmp_path`, run `main(["--input", str(path)])`, assert exit code 0 and (via `capsys`) that the baseline and relaxed variant rows both appear.

Running the tool against the real exported production mention data, and the hand-labelled precision check on top of its output, is LR4 — explicitly not part of this chapter's own test gate. These tests only ever see fixture data constructed in-process or written to a `tmp_path` file.

## Verification

```bash
cd apps/api && ./ci.sh
```

## Refactor gate

Keep `situation_coverage_by_variant` and `format_table` as plain functions operating on the `TaggedMention`/`ThresholdVariant`/`VariantCoverage` types, with `main` staying a thin wrapper (parse args, read file, call the pure functions, print, return an exit code) so the measurement logic itself never needs a file on disk or a DB session to test — the same shape `object_store_probe.py`'s split from `object_store_probe_steps.py` already uses. Run `python -m scripts.measure_code_rules` (or let `ci.sh` run it, if it already does) over the two new files once they exist, to confirm they stay within this repo's own method/parameter-count limits (`apps/api/scripts/measure_code_rules.py:14-16`: 100 lines/class, 5 methods, 3 parameters).

## Commits

- `feat(api): add situation-axis threshold variants and a pure coverage-delta comparison`
- `feat(api): add the measure_situation_tag_coverage CLI over exported mention data`

## Out of scope

Actually changing `settings.discovery_tag_min_procedures`/`discovery_tag_min_share` or `candidate_tags.py`'s production call to `aggregate_tags` — that is a follow-up chapter after this suite's pending T-PENDING decision is settled by LR4's numbers. The "grounded single page" variant (deferred above, pending a mention-schema extension this chapter does not build). A reusable export endpoint or script for pulling `discovery_candidate_mention` rows — LR4 runs a one-off query by hand. The hand-labelled ground-truth sample and its precision check — a live-run human task, not code. Fixing the PVOG dedupe limitation from `discovery-throughput` Chapter 3 — unrelated.
