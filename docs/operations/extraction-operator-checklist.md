# Extraction operator checklist

Every manual action of the extraction suite, in the order it is needed, so no live gate waits for a forgotten console
step. Merging a chapter never waits for a step: the code is tested against fakes. A step unlocks a **live gate**.

Tick the box in the table when a step is done. Write the date and, where a workflow ran, the GitHub Actions run ID (or
the local command) in the same row and in [`run-ledger.md`](../../.plans/extraction/run-ledger.md). Never paste a
secret, a token or an access key into this file, a commit or a chat. The suite and its known gaps:
[loops/extraction.md](loops/extraction.md). Drain behaviour and triage: [discovery-online.md](discovery-online.md) §
LLM kind. Workflows and variables: [scheduled-jobs.md](scheduled-jobs.md). Commands and settings:
[`apps/discovery-ingest/README.md`](../../apps/discovery-ingest/README.md).

The crawlers steps S15 to S21 (Cloudflare token, plan, billing notifications, ledger caps) in
[crawlers-operator-checklist.md](crawlers-operator-checklist.md) come first. The chapter plan numbered these steps X1 to
X10; they are renamed **OP1** to **OP16** here because `X` numbers are decisions in
[`gaps-and-decisions.md`](../../.plans/extraction/gaps-and-decisions.md) (X16 is the model decision).

**Calendar fact.** GitHub Actions minutes are exhausted until the end of October 2026. Remote jobs fail in seconds on
billing until the quota resets (about 2026-11-01). Everything below that says "workflow" can wait for that date or run
as the equivalent local command; nothing else is blocked by it.

## Checklist

| Step | Tick | Date and run ID | What | Needed before |
| --- | --- | --- | --- | --- |
| OP1 | [ ] | | Create the Workers AI token | OP2, OP5 |
| OP2 | [ ] | | Store the secrets in GitHub | `discovery-llm.yml`, `discovery-llm-probe.yml` |
| OP3 | [ ] | | Confirm the Workers Free plan | the first model run |
| OP4 | [ ] | | Optional: tighten `BUDGET_NEURONS_DAILY` | the first model run |
| OP5 | [ ] | | Run the probe | the eval |
| OP6 | [ ] | | Review the gold labels | OP7 |
| OP7 | [ ] | 2026-10-30, `ext-5` eval run by the chief (ledger, "L2 and L3"); X16 decided: Qwen3-30B | Run the eval and decide X16 | OP9, every drain |
| OP8 | [ ] | | Housekeeping: database size, E10 re-pend, fixture capture | any bulk run |
| OP9 | [ ] | 2026-10-30, smoke `bd0e9da9-ff68-43c0-a3cf-25781e18dc4c`, drain `9dee445b-22c8-4d33-9653-8c27eefeb788` (run by the chief) | E6 dry smoke and the E7 live gate (local) | OP12 |
| OP10 | [ ] | | Open and merge the final release PR | OP11 |
| OP11 | [ ] | | Deploy API and web together, re-seed translations, E8 live gate | OP15 |
| OP12 | [ ] | | Backfill and drain, once a day | OP14 |
| OP13 | [ ] | n/a — ships on by default (discovery-throughput chapter 2) | Queue after scheduled renders: no operator action, see Steps for the opt-out | nothing |
| OP14 | [ ] | | Enable the schedule (optional) | nothing |
| OP15 | [ ] | | Review the suggested tags before any emit that carries tags | the first emit with tags |
| OP16 | [ ] | | Native review of the German admin strings | nothing |

The suite's release checklist in [`run-ledger.md`](../../.plans/extraction/run-ledger.md) is complete only when OP1 to
OP12 and OP15 are recorded with dates and run IDs or commands. OP13 ships on by default and needs no operator action
(see Steps); OP14 and OP16 are optional.

## Reported done

Taken from the ledger. They were done in earlier sessions, from the operator's machine, and are recorded there; tick them
after your own check.

- **OP1 and OP5.** A Workers AI token (account-owned, verified active) exists locally. The probe ran on 2026-10-28 on
  three models (about 286 neurons, reported by the API; the probe bypasses the ledger). Results are in the ledger's E4
  row.
- **OP4.** `GET /machine/budgets` on 2026-10-28 returned `neurons` 9500 (no Render override), with `r2_class_a` 950000,
  `r2_class_b` 9500000, `browser_seconds` 570 and `actions_minutes` 400.
- **Evals.** Three evals and one model probe ran on 2026-10-28 and 2026-10-29 (see OP7). The decision is still open.

## Still open

- **OP2 is not done.** On 2026-10-29 `gh secret list` shows no `CLOUDFLARE_AI_API_TOKEN` (the account id exists), and no
  repository variable is set, so neither `DISCOVERY_LLM_SCHEDULE` nor `DISCOVERY_LLM_MODEL` exists.
- **`discovery-llm.yml` is not on `main`.** `gh workflow run discovery-llm.yml` answers 404 until the final release
  (OP10). `discovery-llm-probe.yml` is on `main` since the mid-suite release.
- **E7 and E8 live gates are deferred** (OP9, OP11). E7 needs the owner's go and the model decision; E8 needs the
  release deploy.

## Steps

**OP1: Create the Workers AI token.** Cloudflare dashboard, My Profile, API Tokens, Create Custom Token. Permission: the
narrowest Workers AI permission the probe proves sufficient (start with **Account · Workers AI · Read**; add Edit only if
the probe is refused), limited to this account, no client IP filter. Copy it once. It is **not** a Render variable, not
the Browser Run token, and never committed.

**OP2: Store the secrets.** `gh secret set CLOUDFLARE_AI_API_TOKEN` (and confirm `CLOUDFLARE_ACCOUNT_ID` exists from
crawlers S16: `gh secret list`). Only `discovery-llm.yml` and `discovery-llm-probe.yml` use them. Export both for local
runs. Local runs also need `DISCOVERY_API_URL` and `DISCOVERY_API_KEY`.

**OP3: Confirm the Workers Free plan.** Dashboard, Workers AI usage and Workers plans: the account is on **Workers
Free**, and the daily neuron meter is visible (10,000 neurons). Do not upgrade to Workers Paid: Workers AI would then bill
past the free allowance. Record the date and the plan name (crawlers S19 holds the billing notifications).

**OP4: Optional, set `BUDGET_NEURONS_DAILY` in Render** (default 9,500, 95 percent of the allowance). Only 500 neurons a
day stay unreserved, and Cloudflare's allocation counts every use on the account, including the probe, which bypasses the
ledger. Tighten the variable if other workloads use Workers AI. Check with `GET /api/v1/discovery/machine/budgets`.

**OP5: Run the probe.** Locally, with the two Cloudflare variables exported; note the dashboard's neuron counter before
and after, because the probe bypasses the ledger:

```bash
cd apps/discovery-ingest
python -m discovery_ingest llm probe --model <model id> --fixture tests/fixtures/pages/table_page.html --max-neurons 900
```

The workflow form (after OP2): `gh workflow run discovery-llm-probe.yml -f models=<id>[,<id>] -f max_neurons=900`. Record
the table and the observed neurons. Re-run it for any model you consider that has no probe record.

**OP6: Review the gold labels (about an hour).** The 20 `*.gold.json` files in
`apps/discovery-ingest/tests/fixtures/gold/` were drafted by Claude (14 hosts, 47 gold documents, 2 gold edges). Read each
against its page, correct names, roles and codes, and add documents the labels miss (precision is understated where the
model found real ones). Re-scoring after an edit is free, because the eval cache is keyed on page text, not on labels:

```bash
python -m discovery_ingest llm eval --model <model id> --neuron-budget 5000 --out /tmp/eval.json   # cached pages cost nothing
```

**OP7: Run the eval and decide X16.** Done on 2026-10-30 (the day allows 9,500 neurons; the three evals cost 5,324).
Figures from the live `ext-5` eval on the 20 gold pages (the `ext-4` figures are in the ledger). The quote-grounded
rate is the share of raw model items whose quote is on the page (target 0.95); the kept rate is the share the pipeline
kept (no target); the old "Grounded" column of earlier tables is the kept rate:

| Model | Precision | Recall | Quote-grounded | Kept rate | Tag agreement | Neurons per page |
| --- | --- | --- | --- | --- | --- | --- |
| `@cf/qwen/qwen3-30b-a3b-fp8` (X16 choice) | 0.68 | 0.68 | 0.93 | 0.73 | 0.63 | 63.5 |
| `@cf/meta/llama-4-scout-17b-16e-instruct` | 0.61 | 0.60 | 0.97 | 0.78 | 0.58 | 101.2 |
| `@cf/mistralai/mistral-small-3.1-24b-instruct` | 0.65 | 0.36 | 0.91 | 0.74 | 0.65 | 115.5 |
| `@cf/meta/llama-3.3-70b-instruct-fp8-fast` | not run on `ext-5` (`ext-4`: 0.57, 0.51, kept 0.59, tag 0.71, 154 a page) | | | | | |

Thresholds: precision 0.80, recall 0.60, quote-grounded rate 0.95, tag agreement 0.60. To repeat the eval of a model
(the live run needs the quota to be unspent for the day; Cloudflare answers 429 code 4006 when it is spent):

```bash
python -m discovery_ingest llm eval --model @cf/qwen/qwen3-30b-a3b-fp8 --neuron-budget 4000 --out /tmp/eval-qwen-ext5.json
```

Write decision X16 in `gaps-and-decisions.md` (model, endpoint mode, `PROMPT_VERSION` `ext-5`, `CLEAN_VERSION`
`clean-4`, the four metrics, `neurons_used` of each run, the thresholds later gates use), then set the repository
variable `DISCOVERY_LLM_MODEL` (OP14). `discovery-render.yml`'s job `env` already reads that same variable
automatically (OP13 ships on by default, see Steps), so there is nothing separate to set for the render worker.
`LLM_MODEL` defaults to the X16 choice `@cf/qwen/qwen3-30b-a3b-fp8`, so a drain needs no export; set it only to
choose another model. If no model reaches the targets, record
the shortfall and one of three decisions: accept lower recall because everything is human-reviewed, change the cleaner
or the prompt, or fall back to hand-written extractors for the weak hosts (crawlers chapter 18). If the 70b model is
chosen, revert the E18 code guard with the one-line change in `ground._codes`.

**OP8: Housekeeping that the ledger lists as open.**

1. *Database size against the 475 MB soft limit* (crawlers S8): run `select pg_size_pretty(pg_database_size(current_database()));`
   in the Supabase SQL editor and record it. The extraction staging adds rows for mentions and edges.
2. *E10 re-pend counts and drain.* Count, re-pend once, drain, count again, and confirm `dipul.de` still fails:

   ```sql
   select kind, count(*) from discovery_task
   where status = 'failed' and last_error like '%robots.txt disallows%' group by 1;
   ```

   ```sql
   update discovery_task
   set status = 'pending', claimed_at = null, lease_expires_at = null, last_error = null,
       attempt_count = 0, not_before = null
   where kind in ('fetch_url', 'render_page', 'capture_screenshot')
     and status = 'failed' and last_error like '%robots.txt disallows%';
   ```

   ```bash
   python -m discovery_ingest worker drain --kinds fetch_url --max-tasks 50 --max-batches 10 --time-budget-seconds 600
   ```

   Render kinds wait for their daily browser budget. Record the count before, the count after, and how many hosts
   flipped to allowed.
3. *E2 fixture capture follow-ups.* Capture rendered pages of the hosts the cleaner found weak (the BLE menu and the
   `Fachschüler/innen` whitespace case) as fixtures: `gh workflow run discovery-fixture-capture.yml -f host=<host> -f limit=5`
   then `gh run download <run-id> --name snapshot-fixtures` (needs Actions minutes), or
   `python -m discovery_ingest artifacts list --host <host>` and `artifacts download` locally.

**OP9: E6 dry smoke and the E7 live gate (local).** Needs OP2's local variables (token and account id), OP7's model and
the owner's go, because the run stages candidates, mentions and edges in production and spends neurons. The API on `main`
already has the E1 routes and the E6 stop reasons. Plan it for one day with no other model use. First a one-task smoke,
then the gate:

```bash
# LLM_MODEL defaults to the X16 choice (@cf/qwen/qwen3-30b-a3b-fp8); export it only for another model
export LLM_MODEL=<chosen model id>
python -m discovery_ingest llm requeue --limit 20 --dry-run
python -m discovery_ingest worker drain --kinds llm_extract --max-tasks 1 --max-batches 1 --neuron-budget 1000
python -m discovery_ingest llm requeue --limit 20
python -m discovery_ingest worker drain --kinds llm_extract --max-tasks 5 --max-batches 4 --neuron-budget 2500
```

A budget under about 900 neurons cannot run a 30,000-character page. After the drain, open
`GET /api/v1/discovery/admin/candidates` and a candidate detail: mentions with `extractor = llm`, roles including
`issued`, conditions, suggested tags and edges. Read ten mentions against their source pages and record the precision
(for example "8 of 10 real"), the neurons per page, the ledger's `neurons` figure (`budget show --resource neurons`),
the report's `stop_reason` and `neurons_used`, and confirm a `capture_screenshot` task exists for a page with mentions
and none for a page without. Pages extracted before the capture hook have no screenshot task: `python -m discovery_ingest capture requeue --limit 60` queues them, and the drain cadence is in [candidate-view.md](candidate-view.md#screenshot-cadence). The gate with the workflow (`gh workflow run discovery-llm.yml -f llm_model=<id> (optional, the same default) -f
max_batches=4 -f neuron_budget=2500`) needs OP2, OP10 and Actions minutes.

**OP10: Open and merge the final release PR.** `feat/extraction` into `main`, after the ledger rows E7 to E9 and E12 to
E18 are complete. `main` has only the mid-suite release
([PR #229](https://github.com/vadim-schultz/redtape/pull/229): E11, E10, E1 to E6, plan docs). The PR carries E7, E8, E9
and E12 to E18, including `discovery-llm.yml`, the API change for `llm_outcomes`, the web changes and the translations.
No migration is new beyond `20261029_staging_edges`, which was applied by hand on 2026-10-28. State in the PR body whether
remote CI ran; if Actions minutes are back, wait for it (`gh pr checks --watch`), otherwise merge on the full local CI.

**OP11: Deploy API and web together, re-seed translations, run the E8 live gate.** The web app now requires
`llm_outcomes` from the coverage route, so deploy API and web in the same window (Render for the API, the Workers build
for the web). The API seeds translations on every boot (`scripts/seed_i18n`); check that the `discovery_admin.coverage.llm`
keys exist. Then, as an allowlisted admin, open a staged candidate produced by OP9 and check: conditions, the optional
chip and the `issued` chip, tag chips with "n of total procedures", edges both ways, Coverage `llm_extract` chips and the
neuron meter, light and dark, `de` and `en`, and 360 px. Record the candidate id. Also confirm that `GET /machine/taxonomy`
answers 200 with the active canonical category vocabulary, and open a candidate with no suggested codes to confirm it renders.

**OP12: Backfill and drain, once a day.** Requeue in slices and drain with the local command; watch `neurons_used` and
the stop reason (the ledger caps stop overspend, the dashboard confirms it; a `llm_quota` stop means Cloudflare's own
allocation was used up, so wait for 00:00 UTC):

```bash
python -m discovery_ingest llm requeue --limit 50
python -m discovery_ingest worker drain --kinds llm_extract --max-tasks 5 --max-batches 20 --time-budget-seconds 600 --neuron-budget 2500
python -m discovery_ingest budget show --resource neurons
```

Snapshots that are client-side shells (most of `verwaltung.bund.de`) complete as `no_content`; render them first.
Requeueing the same page under the same model, prompt and cleaner versions queues nothing (the task identity is the
catalogue row, the kind, the target URL and the key), so a daily `llm requeue` is safe. A new model, `PROMPT_VERSION` or
`CLEAN_VERSION` queues the backlog again; do that deliberately, because it spends neurons.

**OP13: Queue after scheduled renders (on by default).** `discovery-render.yml` sets both in the `env` block of its
`drain` job by default:

```yaml
      LLM_ENQUEUE: "true"
      LLM_MODEL: ${{ vars.DISCOVERY_LLM_MODEL }}
```

so scheduled renders queue `llm_extract` work automatically; no operator step is needed for this default. An unset
`DISCOVERY_LLM_MODEL` variable becomes an empty `LLM_MODEL` value, which means no model. With `LLM_ENQUEUE` on and an
empty `LLM_MODEL` the render drain exits 2. A failed enqueue never fails a render; it is counted as
`llm_enqueue_failed`. A laptop render with both variables exported does the same.

**OP14: Enable the schedule (optional).** Only after the OP9 live gate and only after activation step 1 of
`pipeline-activation.md` has passed. Set the repository variables `DISCOVERY_LLM_MODEL` (the OP7 model) and `DISCOVERY_LLM_SCHEDULE=enabled`
(Settings, Secrets and variables, Actions, Variables). The run is daily at 04:30 UTC with 2,500 neurons and skips itself
when the model, the Actions minutes (under 20) or the neurons (under 300) are missing. To pause, delete
`DISCOVERY_LLM_SCHEDULE`; manual dispatch keeps working:
`gh workflow run discovery-llm.yml -f neuron_budget=2500` (add `-f llm_model=<id>` for another model than the default).
Only a scheduled run needs the variable `DISCOVERY_LLM_MODEL`.

**OP15: Review before emitting tags.** Read ten candidates' suggested tags against their procedures in the admin and compare
with the eval's tag agreement. If they disagree, leave tags out of emit (the thresholds `DISCOVERY_TAG_MIN_PROCEDURES` and
`DISCOVERY_TAG_MIN_SHARE` are API settings) and record the finding. Candidate emit itself stays the crawlers routine S10;
edges are never emitted.

**OP16: Native review of the German strings.** A language model wrote the German copy of the E8 screens. Keys to review
(`apps/api/scripts/seed_data/translations/de.json`, with an identical fallback in the web app):

- `discovery_admin.documents.role_issued`, `discovery_admin.tasks.note_no_content`, `discovery_admin.tasks.note_no_documents`
- `discovery_admin.document.col_condition`, `discovery_admin.document.optional`
- `discovery_admin.document.tags.title`, `.categories`, `.support`, `.empty`, `.accepted`
- `discovery_admin.document.edges.title`, `.requires`, `.required_by`, `.empty`, `.basis_explicit`, `.basis_derived_single_issued`, `.procedure`
- `discovery_admin.coverage.llm.title`, `.extracted`, `.no_documents`, `.login_wall`, `.no_content`

## Rotation and rollback

**Rotate the token:** create a new one (OP1), replace the secret (`gh secret set CLOUDFLARE_AI_API_TOKEN`), run the probe
(OP5), delete the old token. **Roll back:** delete `DISCOVERY_LLM_SCHEDULE` and the `CLOUDFLARE_AI_API_TOKEN` secret. `LLM_ENQUEUE` is hard-coded to `"true"` in the `env` block of `discovery-render.yml`, so no repository variable switches it off. Stopping new `llm_extract` work needs an edit to that line. Pending `llm_extract` tasks wait harmlessly and the render and fetch drains are
unaffected. The staged output is additive: nothing was emitted, so there is nothing to undo downstream.
