---
name: "Chapter 3 — PVOG personalMatters as an independent situation signal"
overview: "Thread the Lebenslage code PVOG's client walk already discards through to each mention, mapped against the 12 of 18 situation codes with an unambiguous leaf, so a PVOG-sourced mention can assert its own situation_codes alongside the LLM-extracted page assertion."
todos:
  - id: step-0
    content: "BLOCKING: human spot-check of lr3-personal-matters-mapping.md's 14 ambiguous + 18 clean rows, signed off in situation-tag-coverage/gaps-and-decisions.md"
    status: pending
  - id: mapping-table
    content: "Add situation_mapping.py's PERSONAL_MATTER_TO_SITUATION table, citing the sign-off"
    status: pending
  - id: iter-records
    content: "Change iter_records() to yield (code, record) instead of bare record"
    status: pending
  - id: cli-plumbing
    content: "Unpack the tuple in cli.py's _pvog_run/_map_pvog_records, pass personal_matter_code through"
    status: pending
  - id: map-pvog-record
    content: "Add personal_matter_code param to map_pvog_record, stash into raw_payload"
    status: pending
  - id: mention-draft
    content: "Move domain_codes/situation_codes from MentionItem up onto the base MentionDraft"
    status: pending
  - id: harvest-pvog
    content: "Add _situation_codes() reading the stashed code through the mapping table, thread into _draft()"
    status: pending
  - id: tests
    content: "Table shape, iter_records tuple yield, map_pvog_record stashing, harvest_pvog_payload mapping/exclusion"
    status: pending
  - id: overlap-count
    content: "One-off read-only production count of PVOG/LLM co-mention overlap"
    status: pending
isProject: false
---

# Chapter 3 — PVOG `personalMatters` as an independent situation signal

**Repo:** `redtape` (`apps/discovery-ingest`) · **Branch:** `feat/situation-tag-activation-pvog-situation-signal` · **Status:** planned — blocked on Step 0

**Depends on:** none in code (no dependency on chapters 1/2); **Step 0 human sign-off is a hard prerequisite, see below** · **Decisions:** D4 (`../gaps-and-decisions.md`) — no special-casing in consensus; grows out of `situation-tag-coverage` LR3/T-PENDING's S3 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-situation-tag-activation`

## Blocking prerequisite — Step 0 (not a chapter task)

A human spot-check of `.plans/situation-tag-coverage/lr3-personal-matters-mapping.md`, specifically its 14 "ambiguous" rows and the 18 "clean" rows this chapter's mapping table is built from. Record the sign-off (or corrections) in `situation-tag-coverage/gaps-and-decisions.md` **before** this chapter is implemented. This chapter's mapping table must cite that sign-off, not the raw AI first pass — `lr3-personal-matters-mapping.md` is currently flagged as "an AI first-pass mapping, not yet human-confirmed" (`situation-tag-coverage/02-live-runs.md` LR3). Implementation does not start until this sign-off exists, regardless of where chapters 1/2 are.

## Goal

A PVOG-sourced mention can assert `situation_codes`, using only the 12 situation codes with an unambiguous PVOG leaf (`birth-of-child`, `marriage`, `separation-divorce`, `studying`, `buying-property`, `immigration`, `naturalisation`, `getting-licence`, `buying-vehicle`, `illness-care`, `retirement`, `death-of-relative`). Every bundled/ambiguous leaf (notably `1040300`→`job-loss`+`new-job`, `1050200`→`moving-house`+`renting-home`) is excluded — a many-to-many leaf can't cast one clean vote.

## Design

- New `apps/discovery-ingest/discovery_ingest/pvog/situation_mapping.py`: `PERSONAL_MATTER_TO_SITUATION: dict[str, str]`, the ≤18-entry table, docstring citing the mapping file and the Step 0 human sign-off.
- `apps/discovery-ingest/discovery_ingest/pvog/client.py::iter_records()`: yield `(code, record)` instead of bare `record`.
- `apps/discovery-ingest/discovery_ingest/cli.py::_pvog_run`/`_map_pvog_records`: unpack the tuple, pass `personal_matter_code=code` through to `map_pvog_record`.
- `apps/discovery-ingest/discovery_ingest/pvog/client.py::map_pvog_record`: add `personal_matter_code: str | None = None`; when given, stash it into the stored `raw_payload` under a reserved key (e.g. `"_personal_matter_code"`) before `dict(row)` is captured — confirmed no existing PVOG field uses an underscore-prefixed key.
- `apps/discovery-ingest/discovery_ingest/mentions.py`: move `domain_codes`/`situation_codes` from `MentionItem` up onto the base `MentionDraft` (same `Field(default=None, max_length=...)` shape); `MentionItem` no longer redeclares them. (`_items()` in `worker/harvest.py` needs no change — `draft.model_dump()` already carries whatever fields `MentionDraft` has.)
- `apps/discovery-ingest/discovery_ingest/harvest/pvog.py`: add `_situation_codes(raw_payload) -> list[str] | None` reading `raw_payload.get("_personal_matter_code")` through `PERSONAL_MATTER_TO_SITUATION`; thread into `_draft()` so every `MentionDraft` built from that payload carries it. Reuse the existing `EXTRACTOR = "pvog-payload"` constant as-is.
- **Consensus treatment: no special-casing (D4).** A PVOG mention sits on its own real, distinct `catalogue_service_id`, so when a candidate is also mentioned by a different, LLM-extracted procedure asserting the same situation, the two together can satisfy even the unrelaxed 2-procedure bar — genuine independent corroboration, not just "one more vote under an already-loosened floor." It flows through chapter 1's merged engine completely unmodified.
- The `seen_lb_ids` first-hit-only dedupe (open seam, carried from the parent suite, see `../gaps-and-decisions.md` Open seams) is left as-is per that seam's own disposition — not a blocker for this chapter.

## Tests

- `situation_mapping.py` table completeness/shape test (≤18 entries, every value one of the 18 situation codes, every key a string PVOG leaf code).
- `iter_records()` yields `(code, record)` tuples now — update existing fixture tests.
- `map_pvog_record()` stashes `_personal_matter_code` into `raw_payload` when given, and leaves `raw_payload` unchanged when not given.
- `harvest_pvog_payload()` attaches the right single-element `situation_codes` to a `MentionDraft` built from a payload carrying a mapped code, and attaches nothing when the stashed code isn't in the table (e.g. an ambiguous one, confirming exclusion).

## Verification (in addition to the usual `./ci.sh`)

```bash
cd apps/discovery-ingest && ./ci.sh
```

Plus a one-off, read-only count against production of how often a PVOG-catalogued procedure and an LLM-extracted procedure co-mention the same candidate — this is the one part of the design resting on an unmeasured assumption (how much real overlap exists), cheap and read-only to check, same shape as the earlier `situation-tag-coverage` live-run scripts. Record the result in `../gaps-and-decisions.md`'s Open seams table (the "PVOG/LLM overlap is unmeasured" row).

## Refactor gate

Confirm `grep -rn "domain_codes\|situation_codes" apps/discovery-ingest/discovery_ingest/mentions.py` shows the fields on `MentionDraft`, not redeclared on `MentionItem`. Confirm `_items()` in `worker/harvest.py` needed no change, per the `model_dump()` unpack already confirmed in `../00-architecture.md §3`.

## Commits

- `feat(discovery-ingest): map PVOG personalMatters leaves to the 12 unambiguous situation codes`
- `feat(discovery-ingest): thread the PVOG Lebenslage code through iter_records to map_pvog_record`
- `feat(discovery-ingest): attach PVOG-derived situation_codes to the base MentionDraft`

## Out of scope

Fixing `seen_lb_ids` (open seam, carried from the parent suite); any `MANUAL_EXTRACTOR`-style special-casing of the PVOG mention (D4); the ambiguous/bundled leaves (`job-loss`/`new-job`, `moving-house`/`renting-home`) — excluded by design, not deferred; anything about the consensus engine itself or the confidence tier (chapters 1 and 2 respectively).
