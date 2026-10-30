---
name: Extraction — Live runs
overview: "The live steps of 2026-10-30 that the chief of staff runs after E19 and E20: a smoke call, the first real drain with Qwen, a calibration against the Cloudflare dashboard, the ext-5 eval of three models, the X16 decision and the close-out; with the neuron budget for one UTC day."
isProject: false
---

# Extraction — Live runs

**Rollout:** [01-rollout.md](01-rollout.md) · **Ledger:** [run-ledger.md](run-ledger.md) · **Decisions:** [gaps-and-decisions.md](gaps-and-decisions.md) (X16, X17, X18) · **Operator steps:** [extraction-operator-checklist](../../docs/operations/extraction-operator-checklist.md)

**Who runs this:** the chief of staff, not a `chapter-implementer`. Implementers never spend neurons and never touch production. These steps are the live gates that the chapters deferred (E7 and E8 live gates, OP9 and OP11, and decision X16).

**Aim.** The suite exists to extract the documents (nodes) and the requirement edges for the dependency graph, and to categorise them by life situation and domain. Every step below is judged on that: are the staged documents real, are the edges sensible, are the tags usable. The 20-page gold set has 47 documents and only 2 edges, so edge quality can only be judged on live pages.

## Preconditions

1. The plans PR (this change) is on `main`, so the chief's preflight (`git cat-file -e main:<last chapter>`) passes.
2. `origin/feat/extraction` is fast-forwarded to `main`. On 2026-10-30 it is 48 commits behind and 0 ahead: `git fetch origin && git checkout feat/extraction && git merge --ff-only origin/main && git push origin feat/extraction`. Without this every new chapter branches from stale code.
3. [E19](chapters/19-neuron-overshoot.md) and [E20](chapters/20-quote-grounded-rate.md) are merged into the loop branch (ledger rows `merged`). If the chief runs short of time inside the UTC day, the owner may say "live first": L0 to L2 do not need E19 or E20, and L3 is then run after them.
4. `/home/schult_v/.config/redtape/probe.env` is sourced (never printed) so `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_AI_API_TOKEN`, `DISCOVERY_API_URL` and `DISCOVERY_API_KEY` are set.
5. Runs start from a clean git worktree of the loop branch, `PYTHONPATH` set to its `apps/discovery-ingest`, using the main checkout's `.venv`, so branch switching cannot change the code under a running job.
6. `GET /machine/budgets` shows `neurons` with `used` 0 and `exhausted` false for the current UTC day. (On 2026-10-30 at 07:38 UTC: 0 of 9,500.) Cloudflare resets at 00:00 UTC; the ledger's period is the UTC date.

Ownership: the owner's go for the production drain was given on 2026-10-30 (scope: about 40 pages, Qwen, staged only). A larger drain, a different model in production, or any emit needs a new go.

## Neuron plan for one UTC day (cap 9,500, overshoot allowed by E19)

| Step | Model | Estimated neurons | Basis |
| --- | --- | --- | --- |
| L0 smoke | Qwen | about 80 | one real page, 65 a page on the gold set |
| L1 drain | Qwen | up to 3,500 | about 40 real pages at 65 to 90 each |
| L3a eval `ext-5` | Qwen | about 1,300 | 20 gold pages |
| L3b eval `ext-5` | Llama 4 Scout | about 2,000 to 2,700 | 97 measured on a short page |
| L3c eval `ext-5` | Mistral Small 3.1 | about 2,700 | 134 per page measured |
| Total | | about 9,600 to 10,300 | overshoot is accepted |
| Not today | Llama 3.3 70B | about 3,100 | its `ext-4` numbers and the E18 replay exist; run it on a later day only if the winner is close |

The order puts the pages that answer the aim first (the drain), then the eval from the cheapest and most likely winner to the most expensive. A Cloudflare 429 near the end then costs the least informative run.

## L0 — Smoke run (one page)

```bash
cd apps/discovery-ingest   # in the worktree
python -m discovery_ingest llm requeue --host <a host with rendered text> --limit 1
python -m discovery_ingest worker drain --kinds llm_extract --max-tasks 1 --max-batches 1 --neuron-budget 800
```

Pick a host with text (not `verwaltung.bund.de`: 111 of its 115 snapshots are client-side shells). Expect one finished run with a stop reason and one staged candidate. **A 422 on the run finish means the deployed API lacks the E6 stop reasons (`llm_budget`, `llm_quota`): stop here, spend nothing more, and ask the owner to redeploy the API and web together.** Record the run ID and the ledger delta.

## L1 — Live drain with Qwen (about 3,500 neurons)

`@cf/qwen/qwen3-30b-a3b-fp8` is the default `LLM_MODEL`. `llm requeue` takes one `--host` per call (`--limit` up to 200); call it for four to six hosts (for example `www.arbeitsagentur.de`, `www.ble.de`, `www.bundesarchiv.de`, `www.bzkj.de`, `www.bundesjustizamt.de`) so the sample spans page shapes, about 8 pages each, `--dry-run` first.

```bash
python -m discovery_ingest llm requeue --host <host> --limit 8 --dry-run
python -m discovery_ingest llm requeue --host <host> --limit 8
python -m discovery_ingest worker drain --kinds llm_extract --max-tasks 10 --max-batches 4 --neuron-budget 3500
```

Record: run ID, stop reason, `neurons_used` from the run and from `GET /machine/budgets`, neurons per page, the outcome counts (`extracted`, `no_documents`, `login_wall`, `no_content`).

**Judge it on the aim** (this is the only check on unseen pages, and so also the check for over-fitting of the guards tuned to the 20 gold pages):

1. **Nodes.** Read ten staged mentions against their pages. Count correct documents against all staged ones (precision) and note documents the page names that were missed. Write down every false positive by name: these are the evidence for a possible E21 (guards from live pages).
2. **Edges.** List the staged edges (the explicit ones from the model and the derived `derived_single_issued` ones). Does each edge say "this issued document needs that required document" on the page? Note wrong or missing edges.
3. **Tags.** Read the suggested domain and life-situation codes on the candidates (support is at least 2 procedures and at least 50 percent). Do they match what a person would file the procedure under? Note codes that are invented on non-procedure pages.

Use the machine API (candidate mentions, edges, suggested codes). The admin screens need the owner's web deploy and are an optional second look (OP11).

## L2 — Checkpoint A: ledger against the Cloudflare dashboard (owner)

After the drain, the owner reads the Workers AI neuron counter in the Cloudflare dashboard (Workers AI usage) and the chief compares it with `GET /machine/budgets`. Yesterday Cloudflare answered 429 (code 4006) while the ledger read 5,305; the ledger had read 6,232 on the 28th. The cause is not known (probe and playground calls the ledger never sees, or a window that is not UTC midnight).

| Dashboard against ledger | Action |
| --- | --- |
| Within about 25 percent | Continue with L3 as planned |
| More than 25 percent above | Drop Mistral from L3 (L3c), run Qwen and Scout, record the ratio in the ledger and in a gap row |
| Dashboard shows the day nearly spent | Stop spending; record it; L3 moves to the next UTC day |

Record the ratio and the time of the reading in the ledger either way.

## L3 — Live eval `ext-5` on the 20 gold pages

For each model in this order, with a cache directory outside the repository and the results kept in the scratchpad:

```bash
python -m discovery_ingest llm eval --model @cf/qwen/qwen3-30b-a3b-fp8 --neuron-budget 4000 --cache-dir <outside repo>/evalcache --out <scratchpad>/evalruns/qwen3-30b.json
python -m discovery_ingest llm eval --model @cf/meta/llama-4-scout-17b-16e-instruct --neuron-budget 4000 --cache-dir <outside repo>/evalcache --out <scratchpad>/evalruns/scout.json
python -m discovery_ingest llm eval --model @cf/mistralai/mistral-small-3.1-24b-instruct --neuron-budget 4000 --cache-dir <outside repo>/evalcache --out <scratchpad>/evalruns/mistral.json
```

The model is always priced and the eval refuses to start without the credentials and a readable ledger. A stopped run exits 1 and still writes the finished pages; the cache keeps them, so a stopped model resumes cheaply on a later day. Record per model: precision, recall, **quote-grounded rate and kept rate** (E20), tag agreement, page-kind accuracy, edge precision and recall (only 2 gold edges: noise), neurons used, neurons per page, pages per day. The `ext-4` table in the [ledger](run-ledger.md) is the baseline.

## L4 — Decision X16

Choose by the thresholds in [gaps-and-decisions.md](gaps-and-decisions.md) (precision 0.80, recall 0.60, quote-grounded 0.95, tag agreement 0.60). Where no model meets all, take the model that meets most, then break ties by document recall and tag agreement (the graph needs both nodes and categories), then by neurons per page. Write the final X16 in `gaps-and-decisions.md` with the numbers, the model, the prompt and cleaner versions, and any shortfall with one of the three decisions already named there (accept lower recall because everything is human-reviewed, change the cleaner or the prompt, or hand-written extractors for weak hosts). If the winner is not Qwen, change `DEFAULT_LLM_MODEL` in `llm_settings.py` (a one-line PR into the loop branch).

## L5 — Close-out

1. Fill the ledger: the E19 and E20 rows' notes, the live gates of E7 and E8 (run IDs, neurons, ten-mention precision, a candidate id, edges and tags seen), the `ext-5` table, the dashboard ratio, the day's total at the end (`GET /machine/budgets`; it should read at or slightly above 9,500 when everything ran, not about 8,600), and a fresh session hand-off.
2. Write the list of false positives from L1 as the evidence section of a possible chapter **E21** (name and code guards written from live pages, not from the 20 gold pages). Create E21 only if the list shows a pattern; a one-off is not a guard.
3. When every chapter row is `merged` and the live gates are recorded or deferred with the step they need, open the release PR `feat/extraction` to `main` (second release). Rerun remote CI on it if Actions minutes are back (about 2026-11-01).

## Stop rules

- A Cloudflare 429 with code 4006 ends the day's spend. The run releases its tasks; record it and stop. Nothing is retried in the same UTC day.
- A 422 on the run finish, a 401 from Cloudflare, or a ledger that cannot be read: stop and report. Do not spend without a ledger.
- A drain that stages obvious noise (more than a third of the ten read mentions wrong): stop the drain, do not requeue more, and report the pages. Staging is reversible only by a human reviewer, so it stays small.
- Never emit candidates or edges; never enable the schedule (`DISCOVERY_LLM_SCHEDULE`) in this step.
