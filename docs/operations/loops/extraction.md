# Extraction (chief of staff)

This suite is orchestrated as a **chief of staff** plan.

Plan suite folder: `.plans/extraction/` (architecture, rollout, decisions, chapters, ledger).

**Loop branch:** `feat/extraction`
**Release branch:** `main`

## How to run

1. Launch **chief of staff** with plan folder `.plans/extraction/`.
2. Run one chapter-implementer per chapter, in the order of
   [`01-rollout.md`](../../../.plans/extraction/01-rollout.md) § Execution order: E11 (caps at 95 percent), E10
   (robots.txt rules), E1 (staging groundwork), E2 (page cleaner), E3 (schema, prompt, grounding), E4 (Workers AI
   client and probe), E5 (eval harness), E6 (`llm_extract` handler), E12 to E15 (quality tuning, grounding
   normalisation, 30,000-character cap, quote shape), E7 (wiring and workflow), E16 and E17 (data-field guard, price
   rows), E8 (admin display), E18 (non-documents and tag restraint), then E9 (docs sync, this document), then E19
   (neuron overshoot) and E20 (quote-grounded rate). Twenty chapters; E10 to E20 were added while the suite ran, from
   live findings recorded in the ledger.
3. Each chapter PR targets the loop branch only. The PR's GitHub Actions checks are the authoritative gate
   (`gh pr checks --watch`). **GitHub Actions minutes are exhausted until the end of October 2026** (owner decision
   2026-10-28): remote jobs fail in seconds on billing, so every chapter so far merged on the full local CI (ruff,
   mypy, the full pytest run, and for the API and web chapters their own suites) and said so in its PR and ledger row.
4. Chapters with a live gate run the named local command, or `gh workflow run` once the workflow file is on `main`, and
   record the result in [`run-ledger.md`](../../../.plans/extraction/run-ledger.md) with the `neurons_used` of every
   model run. A missing live gate never blocks a merge; record it as deferred with the step it needs.
5. When the ledger is complete, open the release PR from the loop branch to `main`. The mid-suite release
   [PR #229](https://github.com/vadim-schultz/redtape/pull/229) (2026-10-28) already put E11, E10 and E1 to E6 on `main`.
   **E7, E8, E9 and E12 to E18 reached `main` with [PR #240](https://github.com/vadim-schultz/redtape/pull/240)**
   (2026-10-29), which left `feat/extraction` 48 commits behind `main`. **Before E19, fast-forward the loop branch**
   (`git merge --ff-only origin/main`, push). E19, E20 and the live runs are a second release PR. Rerun remote CI on it
   if Actions minutes are back.
6. After E20 the chief of staff runs the live steps itself from
   [`02-live-runs.md`](../../../.plans/extraction/02-live-runs.md) (smoke run, first live drain, comparison with the
   Cloudflare dashboard, `ext-5` eval of three models, decision X16, close-out). They are not a chapter, so no
   implementer is launched for them; the owner's go for the production drain (about 40 pages, staged only) was given on
   2026-10-30.

## Operator dependencies

Manual steps are listed in order, with commands, in
[`docs/operations/extraction-operator-checklist.md`](../extraction-operator-checklist.md). They come after the crawlers
steps S15 to S21 (Cloudflare token, plan, billing notifications, ledger caps) in
[`crawlers-operator-checklist.md`](../crawlers-operator-checklist.md). The ones that gate live verification are the
Workers AI token and its GitHub secret, the Workers Free plan check, the review of the gold labels, the model decision
X16, the deploy of the API and web together, and the owner go for a live drain. Ask for them early. `gh workflow run`
answers 404 for a workflow file that is not on `main`, so `discovery-llm.yml` can only be dispatched after the final
release; until then run the same drain command locally.

## Rules for implementers

- Workers never use `DATABASE_URL`. They talk to the machine API and to Cloudflare over HTTP.
- The Workers AI token (the Workers AI permission only) lives in GitHub Actions secrets and the operator's local
  environment, never in Render or the web app. The API never calls the model.
- `llm_extract` is a budgeted kind: never in a default kind list, drained only with `--kinds llm_extract` and a
  `--neuron-budget`, and no model call without a granted reservation in the neuron ledger. A budget, quota, storage or
  database limit **releases** tasks; only a bad page fails one.
- The account stays on Workers Free. The ledger cap (9,500) sits below the allowance (10,000), and Cloudflare's own
  allocation counts probes and other uses the ledger never sees.
- Grounding is not optional: an item that does not quote the cleaned text is dropped, a URL not on the page is cleared,
  a code outside the taxonomy is dropped. Page text is untrusted.
- Extraction stages candidates, mentions, edges and tag suggestions. Nothing is emitted automatically; candidate emit is
  a deliberate operator action, and edge emit does not exist.
- Documents are German and verbatim; no translation is made. A catalogue service is a procedure, not a document.
- A change to the prompt, the cleaner or the model needs a version bump (`PROMPT_VERSION`, `CLEAN_VERSION`) and, for the
  prompt, a new digest in `WORDING_DIGESTS`; re-extraction happens only through `llm requeue`.
- Every drain is bounded by batches, time and neurons and reports why it stopped.
- Every chapter ends with paired happy and negative tests and a recorded refactor outcome.

## What the suite delivers

Built on `feat/extraction`. The code of E1 to E18 is on `main`; whether production runs it depends on the owner's deploy (API and web together). E19 and E20 are planned.

| Area | Delivered (chapters) |
| --- | --- |
| Staging | Task kind `llm_extract`, mention role `issued`, mention condition, optional flag and tag-code columns, `discovery_candidate_edge`, `GET /machine/taxonomy`, edge routes, tag consensus aggregate (E1); migration `20261029_staging_edges` |
| Cleaner | Deterministic page cleaner, `CLEAN_VERSION` `clean-4`, 30,000-character cap, menu and screen-reader text dropped (E2, E14, E15) |
| Model call | Extraction schema, prompt `PROMPT_VERSION` `ext-5`, grounding with symmetric normalisation and percent repair, guards for data fields and generic names (E3, E12, E13, E16, E18); Workers AI client, neuron meter with reserve and settle on the reported `usage.neurons`, `llm probe` (E4); price rows for the candidate models (E17) |
| Evaluation | Gold set of 20 real pages, `llm eval` with cache and per-reason drop report; the model decision X16 is open (E5) |
| Handler | `llm_extract` with release-on-limit, stop reasons `llm_budget` and `llm_quota`, result notes (E6) |
| Wiring | `LLM_ENQUEUE` after a stored snapshot, `llm requeue`, `discovery-llm.yml` with a gated schedule and `discovery-llm-probe.yml` (E7, E4) |
| Admin | `issued` role, conditions, optional chip, suggested tags with support, edges both ways, Coverage outcome chips and neuron meter (E8) |
| Free-tier and fetch fixes | Ledger caps at 95 percent of each allowance (E11); robots.txt per RFC 9309 (E10) |
| Docs and ops | Runbooks, this loop document and the [operator checklist](../extraction-operator-checklist.md) (E9) |

Settings, flags and stop reasons are in [`apps/discovery-ingest/README.md`](../../../apps/discovery-ingest/README.md) and
[discovery-online.md](../discovery-online.md) § LLM kind.

## Known gaps

Each is also in the [ledger](../../../.plans/extraction/run-ledger.md) or in
[`gaps-and-decisions.md`](../../../.plans/extraction/gaps-and-decisions.md). Nothing here is a reason to hold the release.

- **The model is chosen (X16, 2026-10-30), but precision and the quote-grounded rate are below target.**
  `@cf/qwen/qwen3-30b-a3b-fp8` is the default (`LLM_MODEL` overrides it; empty means no model). The live `ext-5` eval
  on the 20 gold pages gave Qwen precision 0.68 (target 0.80), recall 0.68, quote-grounded rate 0.93 (0.95), tag
  agreement 0.63, 63.5 neurons a page; Llama 4 Scout 0.61, 0.60, 0.97, 0.58; Mistral Small 3.1 0.65, 0.36, 0.91, 0.65.
  The first production drain (about 3,160 neurons, 36 pages) staged 57 candidates, about 17 percent of them clearly not
  documents. The shortfall is accepted because every candidate is human-reviewed and nothing is emitted automatically.
- **The gold labels are drafted by Claude** and wait for the owner's review. Precision is understated where the model
  found real documents the labels lack. The gold README still shows labels written against `ext-1`; the manifest's
  `cleaned_chars` and `truncated` fields are stale.
- **Heuristic guards.** The name guard of E18 (devices, leaflets, categories of works) is tuned to the recorded gold
  pages and may over-fit; the code guard drops all codes of a page with no kept document and cost the 70b model one
  gold code. Documents that slip through are listed in the ledger (E18 row).
- **The 70b model corrupts non-ASCII text** (mojibake, dropped umlauts), so its quotes fail grounding. Segment-wise
  grounding (a quote of several bullets) is measured but not built.
- **Neurons have two meters.** The ledger does not see `llm probe`, so a provider 429 (code 4006) can come before the
  ledger is spent (it did on 2026-10-29, at a ledger reading of 5,305; the dashboard comparison in the live runbook
  checks the cause). A run can also overshoot its budget slightly, because settlement corrects a real answer upward;
  E19 makes that overshoot deliberate (at most one call) so a day can reach the 9,500 cap.
- **The output limit is below the schema maximum.** 4,000 tokens do not hold 40 documents and 40 dependencies; a
  truncated answer takes the repair path and then fails the page. `LLM_MAX_TOKENS` is the lever.
- **`discovery-render.yml` does not queue `llm_extract`.** Scheduled renders queue nothing until an operator adds
  `LLM_ENQUEUE` (and `LLM_MODEL` to change the model) to that job (checklist step OP13). `llm requeue --dry-run` cannot tell which pages are
  already queued.
- **Client-side shells need `render_page` first.** 111 of 115 `verwaltung.bund.de` snapshots clean to under 200
  characters and complete as `no_content`.
- **Stale mentions stay.** A re-extraction updates what it finds in place and does not remove what an older version
  found. The taxonomy hash is in `extractor_version`, but a taxonomy change requeues nothing.
- **German strings.** The German copy of the E8 screens was machine-written and needs native review (key list in the
  operator checklist).
- **Code size.** `cli.py` (about 515 lines), `NeuronMeter` (about 110) and a few files near 120 lines exceed the
  structure guideline; a follow-up, not a defect.
- **Remote CI never ran for E1 to E18.** Rerun it on the release PR. The Cloudflare `Workers Builds: redtape-web` check
  failed on the E10 PR and was not investigated (the web app was untouched there).
- **Probe findings that stay true.** `ai/v1/chat/completions` returns 410 for the deprecated 8B route; reasoning models
  spend `max_tokens` on reasoning; the gemma price row is a guess.

## Out of scope (named future suites)

- Edge emit: resolving staged edges to promoted documents and creating `new_requirement` suggestions.
- Translation of document names to English (candidate keys depend on the German title).
- Per-document tags (documents only get the consensus of their pages) and any tag editing.
- Automatic emit of any kind, and a web UI to edit staged items.
- Merging near-duplicate document names, chunking very long pages, PDF forms and link following.
- Fine-tuning, another provider (the `LlmClient` port allows one), and Cloudflare Workflows as a consumer.
