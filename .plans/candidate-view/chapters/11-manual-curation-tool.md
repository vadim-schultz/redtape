---
name: "Chapter 11 — Manual curation tool"
overview: "A read-only `candidates page` aid and a file-driven `candidates curate` command in discovery-ingest that applies a reviewed curation file (manual tags and edges for chosen candidates) through the existing machine mention and edge routes, marked extractor manual, with a dry run and a strict validator; used by the showcase curation live run."
todos:
  - id: schema
    content: "Curation file schema (pydantic) with validation against the taxonomy and the grounding rule"
    status: pending
  - id: planner
    content: "Pure planner turns a curation file into MentionItem and EdgeItem batches"
    status: pending
  - id: command
    content: "candidates curate --file --dry-run: validate, plan, post, report; idempotent"
    status: pending
isProject: false
---

# Chapter 11 — Manual curation tool

**Repo:** `redtape` (`apps/discovery-ingest`, docs) · **Branch:** `feat/candidate-view-curation-tool` · **Status:** planned  
**Depends on:** [01-capture-requeue.md](01-capture-requeue.md) (the machine sources route and its `candidate_id` filter), [02-completeness-read-model.md](02-completeness-read-model.md) (the `manual` extractor is meaningful only once the override is deployed) · **Architecture:** [../00-architecture.md](../00-architecture.md) (section 12) · **Decisions:** D18, D19 · **Rollout:** [../01-rollout.md](../01-rollout.md) · **Used by:** [../02-live-runs.md](../02-live-runs.md) LR2

**Loop branch:** `feat/plans-candidate-view` · **Release branch:** `main`

**Order:** executes right after chapter 2 (and so after chapter 1) (see the execution order in the rollout); it needs no web code.

## Goal

The owner wants a handful of **complete candidates made by hand** so that the new pages can be checked against realistic data (a long title, one-sided and two-sided dependencies, many neighbours, tags on both axes, a screenshot). Production candidates are sparse, so the gaps (domain, life situation, edges) are filled by a curator reading the source page. The machine API already accepts mentions and edges with an `extractor` name; what is missing is a **reviewable, replayable, validated** way to send them. Hand-written `curl` is neither.

This chapter adds that tool and nothing that writes outside the existing machine routes: no new route, no migration, no delete.

## Contract

### Curation file

JSON (or YAML if `pyyaml` is already a dependency of `discovery-ingest`; otherwise JSON only), committed under `docs/operations/candidate-curation/<name>.json` by the live run so the decisions are reviewable in a PR. Shape (`curation.py`, pydantic, `extra="forbid"`):

```json
{
  "version": 1,
  "curator": "chief-of-staff 2026-10-30",
  "candidates": [
    {
      "candidate_id": "uuid (documentation only; checked against the title and procedure)",
      "catalogue_service_id": "uuid of the procedure page the curator read",
      "title_de": "Meldebescheinigung",
      "domain_codes": ["identity-civil-status"],
      "situation_codes": ["moving-house"],
      "tag_note": "why these codes (one line)",
      "requires": [
        {"title_de": "Personalausweis", "excerpt": "verbatim sentence from the page", "condition": null, "is_optional": false}
      ],
      "required_by": [
        {"title_de": "Anmeldung einer Wohnung", "excerpt": "verbatim sentence from the page", "condition": null, "is_optional": false}
      ]
    }
  ]
}
```

### Validation (before any call; every failure names the entry and field)

1. Codes: every `domain_codes` (at most 2) and `situation_codes` (at most 3) entry exists in `GET /machine/taxonomy` (`DiscoveryMachineClient.get_taxonomy`); an unknown code fails the whole file, never silently dropped (the API would drop and count it, which hides a typo).
2. Titles: non-blank, at most 120 characters, German as written on the page; the key of a candidate is the slug of its title in the procedure's jurisdiction, as everywhere else, so the title must **equal** the staged candidate's title (the command resolves the staged candidate through `list_staged_candidates` and refuses a title that creates a new candidate by typo, unless the entry sets `"create": true`, which is only for a missing neighbour).
3. Excerpts: non-blank, at most 300 characters, and **grounded**: when the command is given `--check-pages` (default on), it downloads the newest `html_snapshot` of the procedure (`GET /machine/artifacts/{id}/content`), runs the existing cleaner (`extract/cleaner`) and requires the excerpt to be a substring of the cleaned text after the same `normalise()` the extraction grounding uses. A curator cannot invent a quote. `--no-check-pages` exists for pages that need a render and is reported loudly.
4. Edges: `requires` and `required_by` entries produce `parent requires required` edges (`requires`: this candidate is the parent; `required_by`: the other is the parent); self-edges and duplicates are rejected in the file.
5. At most 8 candidates and 60 edges per file (a showcase, not a bulk import).

### Reading aid: `candidates page`

`python -m discovery_ingest candidates page --candidate-id UUID [--out DIR]` is read-only. It calls the machine sources route of chapter 1 with `candidate_id`, and for each procedure row prints `catalogue_service_id`, `source_url`, `host` and `has_screenshot`; with `--out` it downloads the newest `html_snapshot` (`GET /machine/artifacts/{id}/content`), cleans it with the existing cleaner and writes `<DIR>/<catalogue_service_id>.txt`, so the curator reads exactly the text the grounding check will compare against. It exists because the public API hides catalogue ids and the machine key cannot read mentions.

### Plan and calls

- The pure planner `plan_curation(file, staged) -> CurationPlan` returns the `MentionItem` list and the `EdgeItem` list; nothing is posted by it.
- **Tags:** one mention per candidate with `extractor="manual"`, `extractor_version="1"`, `role` of the candidate's existing strongest mention, `source_field="manual:tags"`, `excerpt` = the file's first grounded excerpt or the candidate's existing excerpt, `title_i18n={"de": title}`, the file's codes. Unique per (candidate, procedure, role, source_field), so a re-run updates it. The override of chapter 2 makes it authoritative.
- **Neighbours:** a neighbour that is not yet a candidate (`"create": true`) gets a `manual` mention (`role="required"`, `source_field="manual:neighbour"`, the edge's excerpt) on the same procedure; the edge post needs both ends to exist (post mentions first, as the API says).
- **Edges:** `EdgeItem(basis="explicit", extractor="manual", extractor_version="1", catalogue_service_id, parent_title_i18n, required_title_i18n, excerpt, condition, is_optional)`.
- Calls: `DiscoveryMachineClient.post_mentions` then `post_edges` (batches of at most 100, existing methods). The command prints one line per candidate (`<title> tags=<n> edges=<n>`) and a final `mentions_created= mentions_updated= edges_created= edges_updated= edges_skipped= unknown_codes= dry_run=`. A non-zero `edges_skipped` or `unknown_codes` exits 1.
- `--dry-run` validates, plans and prints the same lines with `dry_run=true`; it makes **no** write call (it may read taxonomy, candidates and snapshots).
- Idempotent: all identities are the API's unique keys, so a second run reports `updated` and creates nothing.
- Settings: only `DISCOVERY_API_URL` and `DISCOVERY_API_KEY`; no Cloudflare or storage setting is needed.

### Reversal (documented, not built)

There is no machine delete. The operator doc (chapter 10) carries the SQL for the owner: delete `discovery_candidate_edge` rows with `extractor = 'manual'`, then `discovery_candidate_mention` rows with `extractor = 'manual'`, then candidates left with no mention and `status = 'staged'`. This chapter writes that SQL into the command's `--help` epilogue and the ingest README.

## Red tests

`apps/discovery-ingest/tests/test_candidates_curate.py` (fakes for the machine client, as in `test_llm_requeue.py`):

| Test | Asserts |
| --- | --- |
| `page prints the procedures of a candidate` | Happy: the fake sources route is called with `candidate_id`; the lines carry id, URL, host, screenshot flag; no write call. |
| `page writes the cleaned text` | Happy: with `--out`, the file content equals the cleaner's output for the fake snapshot. |
| `page for an unknown candidate prints nothing and exits 1` | Negative: an empty page is reported as `no procedures for <id>`. |
| `plan turns a curated candidate into one tag mention and its edges` | Happy: one `manual` mention with the codes, the right source field, and edges in the right direction for `requires` and `required_by`. |
| `curate posts mentions before edges and prints the totals` | Happy: call order, batch sizes, final report line. |
| `curate is idempotent` | Happy: the fake API answers `updated` on the second run; exit 0, nothing created. |
| `dry run makes no write call` | Happy: only read calls happen; `dry_run=true` in the report. |
| `unknown taxonomy code fails the whole file` | Negative: nothing posted; the message names the entry and the code. |
| `title that does not match a staged candidate is refused` | Negative: without `create`, a typo does not create a candidate; message names the closest staged title. |
| `ungrounded excerpt is refused` | Negative: an excerpt not in the cleaned page text fails with the entry named; `--no-check-pages` lets it through with a warning line. |
| `self edge and duplicate edge are refused` | Negative: validation error before any call. |
| `more than eight candidates is refused` | Negative: the bound is enforced. |
| `skipped edges exit non-zero` | Negative: the API reports `unknown_parent`; the command exits 1 and prints the skip reasons. |
| `curation file with an unknown key is rejected` | Negative: `extra="forbid"`. |

## Green

1. `curation.py` models and validators (taxonomy, titles, bounds), then the grounding check with the existing cleaner and `normalise`.
2. `plan_curation` pure function.
3. `candidates_cli.py`: argparse (`candidates page`, and `candidates curate --file --dry-run --check-pages/--no-check-pages`), wiring in `cli.py` next to the other registrars, reporting.
4. Ingest README section and the `--help` epilogue with the reversal SQL.

## Files

**Create**

- `apps/discovery-ingest/discovery_ingest/curation.py` (models, validation), `curation_plan.py` (planner), `candidates_cli.py` (command), tests beside `tests/`

**Edit**

- `apps/discovery-ingest/discovery_ingest/cli.py` (register), `apps/discovery-ingest/README.md`

**Do not edit**

- API code, migrations, the extraction cleaner or grounding (import only), any web code

## Refactor gate

Audit the new modules: each function about 5 lines, files about 100 lines (split models from validators), strict types (no `Any`), docstrings, no copy of `_limit_arg`-style helpers (reuse), the `manual` literal defined once (`MANUAL_EXTRACTOR`, shared with the API constant by value; a test pins both to `"manual"`). Report the outcome.

## Verification

```bash
cd apps/discovery-ingest && pytest tests/test_candidates_curate.py && cd ../..
./ci.sh
```

## Commits

`test(ingest): define the candidates curate command`, `feat(ingest): add the file-driven manual curation command`.

## Out of scope

Choosing the candidates or writing the file (the live run does), a web editor, deleting or editing existing extracted rows, bulk imports, translating titles, any emit.
