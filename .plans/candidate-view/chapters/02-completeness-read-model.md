---
name: "Chapter 2 — Completeness read model"
overview: "One repository query computes the five completeness flags and their count for every candidate, with the tag consensus and the manual-tag override re-expressed in SQL and pinned to the Python rule by a parity test; the public and admin lists both build on it."
todos:
  - id: consensus-sql
    content: "Accepted domain and situation codes per candidate in SQL, with the settings thresholds"
    status: pending
  - id: flags
    content: "has_edges, has_snapshot, has_screenshot, completeness and complete as selectable and sortable expressions"
    status: pending
  - id: manual-override
    content: "A mention with extractor manual carries authoritative codes that replace the consensus for that axis, in Python and SQL"
    status: pending
  - id: parity
    content: "Parity test: SQL consensus and the manual override equal the Python rule on shared fixtures"
    status: pending
isProject: false
---

# Chapter 2 — Completeness read model

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/candidate-view-completeness` · **Status:** planned  
**Depends on:** none (independent of chapter 1) · **Architecture:** [../00-architecture.md](../00-architecture.md) (section 3) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-candidate-view` · **Release branch:** `main`

## Goal

"Complete" is not defined anywhere: tags are string arrays on mentions, the consensus exists only in Python (`features/discovery/tags.py` `aggregate_tags`, `candidate_tags.py`), and artifacts hang off procedures. Listing, sorting and filtering by completeness (decision D1) must be done in the database. This chapter builds the one query for it (decision D6) and nothing else: no route, no DTO beyond a frozen result row, no migration.

## Contract

### Flags (per candidate)

| Flag | SQL meaning |
| --- | --- |
| `has_domain` | The candidate has at least one **accepted** domain code. |
| `has_situation` | The same for situation codes. |
| `has_edges` | `EXISTS` an edge row with `parent_candidate_id = c.id OR required_candidate_id = c.id`. |
| `has_snapshot` | `EXISTS` mention `m` of the candidate and artifact `a` with `a.catalogue_service_id = m.catalogue_service_id AND a.kind = 'html_snapshot'`. |
| `has_screenshot` | The same with `kind = 'screenshot'`. |
| `completeness` | The number of true flags, 0 to 5 (sum of the booleans cast to integer). |
| `complete` | `completeness = 5`. |

### Accepted code (mirrors `aggregate_tags`)

Per candidate and per axis (domain, situation), over its mentions:

1. A code counts **once per distinct procedure** (`catalogue_service_id`) however many mentions carry it: `COUNT(DISTINCT catalogue_service_id)` per `(candidate_id, code)` over `unnest(<axis>_codes)`.
2. `tagged` is the number of distinct procedures that carry **any** code of that axis (untagged mentions do not dilute): `COUNT(DISTINCT catalogue_service_id) FILTER (WHERE cardinality(<axis>_codes) > 0)` per candidate. A `NULL` array and an empty array both mean "no code" (`unnest(NULL)` yields no row).
3. A code is accepted when `procedures >= settings.discovery_tag_min_procedures` (default 2, `config.py:85-93`) **and** `procedures / tagged >= settings.discovery_tag_min_share` (default 0.5). Compare with a cross-multiplication in integers (`procedures * 1.0 / tagged`, or `procedures >= min_share * tagged` in numeric) and make the boundary case (exactly 0.5) pass, as the Python `>=` does.
4. The axis flag is `EXISTS` an accepted code. The query also exposes the accepted codes themselves as an array (`accepted_domain_codes`, `accepted_situation_codes`) because chapter 3 needs them for the card tags without a second pass.
5. Thresholds are passed in as bind parameters from `settings`; they are not hard-coded and not read inside SQL.
6. Unknown codes (not in the taxonomy) cannot occur: `candidate_codes.py` `CodeVocabulary` drops them at write time. The query does not join the taxonomy; names are resolved by the service in chapter 3.

### Manual override (decision D18)

A candidate can be curated by hand (chapter 11, [../02-live-runs.md](../02-live-runs.md) LR2). A mention whose `extractor` is `manual` is the curator's word, and one procedure is enough for it:

1. Per axis, if **any** mention of the candidate has `extractor = 'manual'` and a non-empty `<axis>_codes`, the accepted codes of that axis are exactly the union of the codes on its manual mentions. The extracted consensus for that axis is ignored (replaced, not merged: a curator who tags `housing` does not also inherit a model guess). Axes are independent: manual domains with extracted situations is allowed.
2. Without such a mention the consensus rule above applies unchanged.
3. Python is the reference: add `curated_codes(mentions)` and `MANUAL_EXTRACTOR = "manual"` to `features/discovery/tags.py` (pure; `aggregate_tags` itself is untouched), and make `candidate_tags.candidate_tag_suggestions` return, for an overridden axis, one `TagSupport(code, procedures=<distinct procedures carrying it>, share=1.0, accepted=True)` per curated code. The detail page's tag suggestions, the emit preview and the SQL read model therefore agree. The emit path takes manual codes the same way (they are accepted codes); that is intended, and the emit review step (OP15) still applies.
4. SQL mirrors it: per axis an `EXISTS` on a manual mention with `cardinality(<axis>_codes) > 0` selects the manual branch (`array_agg(DISTINCT code)` over manual mentions) before the consensus branch; one `CASE`, no second query.
5. A manual mention counts in `mention_count` and in the roles of the candidate like any mention; that is stated in the PR and the operator doc, not hidden.

### Module and shape

New repository module `apps/api/app/features/discovery/repository/candidate_completeness.py` (discovery repositories are split per aggregate and composed in `composite.py:21-37`; the completeness query is about candidates, and chapter 3's `features/candidates` package consumes it through the composed repository). It exposes:

- `completeness_subquery(thresholds: TagThresholds) -> Subquery`: one row per candidate id with the five booleans, `completeness` and the two accepted-code arrays; built from small named CTE helpers (`_axis_acceptance(column, thresholds)`, `_edge_flag()`, `_artifact_flag(kind)`), each a few lines.
- `completeness_columns(sub)` returning the labelled columns and `completeness_order(direction)` returning the ordering expression pair `(completeness, mention_count)` so chapters 3 and 4 do not re-derive them.
- `TagThresholds(min_procedures: int, min_share: float)` frozen dataclass with `from_settings(settings)`; and `CandidateCompleteness` frozen dataclass (the row type with the booleans, `completeness: int`, `complete: bool`, accepted code tuples).

The query is a **left join target** keyed by candidate id so the existing listings (`candidate_listing.py:61-80`) can join it without changing their stats subquery.

## Red tests

`apps/api/tests/test_candidate_completeness.py`, DB-backed (`db_session`, inline `_candidate`, `_mention`, `_artifact`, `_catalogue` helpers as in `test_discovery_candidates_admin_api.py:34-96`; remember `autoflush=False`: `session.flush()` after adds).

| Test | Asserts |
| --- | --- |
| `a candidate with every signal is complete` | Two procedures both tagging `housing` and `moving-house`, an edge, a snapshot and a screenshot on a mentioned procedure: five flags true, `completeness == 5`, `complete`. |
| `a candidate with nothing is zero` | A bare candidate with one untagged mention: all flags false, `completeness == 0`. |
| `a single procedure never reaches the tag consensus` | Negative: one procedure carries `housing`; `has_domain` is false (support 1 < 2) although the mention is tagged; the accepted code array is empty. |
| `the share rule excludes a minority code` | Five tagged procedures: `a` on four, `b` on two. With `min_share` 0.5, `b` has two procedures but a share of 2/5 = 0.4, so it is not accepted while `a` (4/5) is. |
| `untagged mentions do not dilute the share` | Two procedures tagged `a` plus three untagged mentions on other procedures: `a` accepted (share 2/2). |
| `a duplicate mention on one procedure counts once` | Negative: two mentions of the same procedure both carrying `a`: support is 1, not accepted. |
| `the share boundary is inclusive` | Exactly 0.5 with two procedures: accepted, as in Python. |
| `edges count on either end` | Candidate only as `required` end of an edge: `has_edges` true; a candidate in no edge: false. |
| `snapshot and screenshot count on any mentioning procedure` | Artifacts on a procedure that does not mention the candidate do not count (negative); on a second mentioned procedure they do. |
| `completeness order is completeness then mentions` | Three candidates: order by completeness descending, ties by mention count descending. |
| `sql consensus matches aggregate_tags` | **Parity.** A table of at least 12 fixtures (empty, single, minority, boundary, duplicates, `NULL` and empty arrays, three codes) is run through `aggregate_tags` (accepted codes) and through the SQL; the accepted sets are equal for both axes and for non-default thresholds (`min_procedures=1`, `min_share=0.75`). |
| `a manual mention overrides the consensus for its axis` | A candidate whose extracted mentions agree on `housing` on two procedures and which has one `manual` mention tagged `work-employment`: accepted domains are exactly `work-employment`; `has_domain` true. |
| `one manual mention on one procedure is enough` | A candidate with a single procedure and a single manual mention carrying a domain and a situation: both flags true (a single extracted mention never is). |
| `the override is per axis` | Negative: manual domains only; the situation axis still follows the consensus (false with one extracted procedure). |
| `an empty manual code list overrides nothing` | Negative: a `manual` mention with `NULL` or empty codes leaves the consensus in force. |
| `manual rows never leak to other candidates` | Negative: a manual mention on candidate A does not change B's accepted codes. |
| `the python rule and the sql agree on manual fixtures` | Parity: the fixtures of the parity table include `manual` rows (override, empty, mixed axes) and `candidate_tag_suggestions` equals the SQL accepted arrays. |
| `thresholds come from settings` | `TagThresholds.from_settings` reads `discovery_tag_min_procedures` and `discovery_tag_min_share`; monkeypatching them changes the result (negative to a hard-coded rule). |

Write and run these before implementing; confirm each fails for the right reason.

## Green

1. `TagThresholds`, `CandidateCompleteness`, and the axis-acceptance CTE with the parity table first (it is the riskiest part).
2. Edge, snapshot and screenshot flags as `EXISTS` subqueries.
3. Assemble `completeness_subquery`, the sum, the ordering helper.
4. Compose it in `composite.py` and expose one read method `completeness_for(candidate_ids)` (used by chapter 3's detail) and the subquery builder (used by the list repositories).
5. Check the plan with `EXPLAIN` on a seeded 2,000-candidate set once and record the timing in the PR description (a note for the open seam "completeness performance"; no threshold is asserted in CI).

## Files

**Edit**

- new `apps/api/app/features/discovery/repository/candidate_completeness.py` (split into `candidate_completeness_tags.py` if over 100 lines)
- `apps/api/app/features/discovery/repository/composite.py`
- `apps/api/tests/test_candidate_completeness.py` (new)

- `apps/api/app/features/discovery/tags.py` (add `MANUAL_EXTRACTOR` and `curated_codes`; `aggregate_tags` unchanged) and `candidate_tags.py` (the override), with their existing tests extended

**Do not edit**

- The consensus thresholds or `aggregate_tags` behaviour (the Python rule stays the reference for extracted tags; the emit path keeps using it through `candidate_tag_suggestions`)
- Models, migrations, `candidate_listing.py`, controllers, schemas (chapters 3 and 4 wire it in)

## Refactor gate

Audit the new module and `composite.py`: every function about 5 lines, one nesting level, no `Any`/`object` in annotations, docstrings on public items, a small enum or constant for the axis column names instead of repeated strings (rule of three: domain, situation, and the artifact kinds), no duplicated threshold logic. Keep the override in one named helper per side (`curated_codes` in Python, `_manual_branch` in SQL) rather than inlined conditions. Run `tests/test_discovery_repository_split.py` (repositories only run queries). Report what was extracted or "audited, nothing needed".

## Verification

```bash
cd apps/api && pytest tests/test_candidate_completeness.py tests/test_discovery_tags.py tests/test_discovery_repository_split.py tests/test_discovery_candidates_admin_api.py
cd ../.. && ./ci.sh
```

## Commits

`test(api): define the candidate completeness flags`, `test(api): pin the sql tag consensus to aggregate_tags`, `feat(api): let a manual mention override the tag consensus`, `feat(api): add the completeness read model`.

## Out of scope

Routes and DTOs (chapters 3 and 4), a persisted column, a materialised view, changing the extracted-tag consensus rule, a taxonomy join, a way to write manual mentions (chapter 11), caching.
