---
name: "Candidate view — Live runs"
overview: "The two live runs of the chief of staff: LR1 collects screenshots for the pages that were categorised (measure the queue, requeue, drain within the browser-seconds cap, verify); LR2 hand-completes the highest-ranking candidates as showcase data for checking the new pages (select, read the pages, write and review a curation file, apply it, capture their screenshots, verify)."
isProject: false
---

# Candidate view — Live runs

**Rollout:** [01-rollout.md](01-rollout.md) · **Ledger:** [run-ledger.md](run-ledger.md) · **Decisions:** [gaps-and-decisions.md](gaps-and-decisions.md) (D12, D14) · **Operator steps:** [crawlers-operator-checklist](../../docs/operations/crawlers-operator-checklist.md), [discovery-online](../../docs/operations/discovery-online.md)

**Who runs this:** the chief of staff, not a `chapter-implementer`. Implementers never spend browser seconds and never touch production. LR1 runs after chapter 1; LR2 after chapters 2, 3 and 11 and LR1.

**Aim of LR1.** The suite's pages are worth opening only if the candidates have a screenshot of the page they came from. As of 2026-10-30 production has none: `llm_extract` queues a `capture_screenshot` task after mentions, but `capture_screenshot` is in no default drain kind and no drain was run. This runbook collects them for the pages that extraction categorised.

## Authority and limits

**LR1.** The owner's request of 2026-10-30 ("trigger screenshot collection for the pages that were categorised in the previous stages") is the go for this spend: Cloudflare Browser Run seconds up to the daily cap (570 s, shared ledger `browser_seconds`), R2 writes of 60 to 300 KB a page, staged data only. One UTC day's cap per run of this document. Anything larger, any other task kind, or any emit needs a new go.

## LR1 — Screenshot collection

### Preconditions

1. [Chapter 1](chapters/01-capture-requeue.md) is merged into the loop branch.
2. **The API carrying chapter 1's machine route is deployed to production** (`GET /api/v1/discovery/machine/candidates/sources` answers 200 with the machine key, including the `candidate_id` filter). The owner deploys. If it answers 404, record the blocker and use the fallback in "Fallback without the route" below only if the owner says so; otherwise continue with the other chapters and return here before chapter 10.
3. `/home/schult_v/.config/redtape/probe.env` is sourced (never printed) so `DISCOVERY_API_URL`, `DISCOVERY_API_KEY`, `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_BROWSER_API_TOKEN` are set.
4. Runs start from a clean git worktree of the loop branch, `PYTHONPATH` set to its `apps/discovery-ingest`, the main checkout's `.venv` used (branch switching must not change the code under a running drain).
5. `GET /machine/budgets` shows `browser_seconds` with room (at least 60) and `exhausted` false for the current UTC day.

### S0 — Measure

```bash
H="X-API-Key: $DISCOVERY_API_KEY"; B="$DISCOVERY_API_URL/api/v1/discovery/machine"
curl -s -H "$H" "$B/artifacts/status"                         # storage_enabled must be true
curl -s -H "$H" "$B/tasks/summary?kinds=capture_screenshot"   # pending_ready, completed, failed
curl -s -H "$H" "$B/artifacts?kind=screenshot&limit=1"        # total screenshots now
curl -s -H "$H" "$B/candidates/sources?missing=screenshot&limit=1"   # total pages still without one
python -m discovery_ingest budget show --resource browser_seconds
```

Record the four numbers. Expected from the 2026-10-30 ledger: `screenshot` total 0; `pending_ready` somewhere between 0 and about 30 (queued by `llm_extract`, count unknown); pages without a screenshot about 25 to 40.

### S1 — Requeue

If `pending_ready` already covers the pages that lack a screenshot, skip to S2. Otherwise:

```bash
python -m discovery_ingest capture requeue --limit 60 --dry-run
python -m discovery_ingest capture requeue --limit 60
```

The dry run prints `pages=`, `queued=0`, `dry_run=true`; the real call prints `queued=`, `already_queued=`, `failed=`. Identity is (catalogue row, kind, URL, `shot@1`), so a re-run is harmless. Record the counts. A non-zero `failed` stops the step: read the stderr lines, do not retry blindly.

### S2 — Drain

Small batches, because a limit releases the whole batch:

```bash
python -m discovery_ingest worker drain --kinds capture_screenshot \
  --max-tasks 5 --max-batches 20 --time-budget-seconds 900 --browser-budget-seconds 570
```

Cloudflare allows one request every 10 seconds and the worker waits 11, so about 55 to 65 pages fit in 900 seconds. Record the run ID, `stop_reason`, `completed`, `released`, `failed`, `browser_seconds_used` and `capture_enqueue_failed`. Stop reasons `browser_budget` and `browser_quota` are normal ends of the day; `storage_unavailable` is a blocker (check `artifacts/status`). Login-wall and oversize pages complete with a note and store nothing; an error status fails the task. Stay inside the day's 570 browser seconds; a second drain on the same UTC day only uses what is left (LR2 may need that or the next day).

### S3 — Verify

1. `GET /machine/artifacts?kind=screenshot&limit=1`: `total` rose by the number completed. Record the total and one artifact ID.
2. `GET /machine/artifacts/status`: `bytes_used` rose by roughly 60 to 300 KB a page; record it against the 9.5 GB cap.
3. `GET /machine/budgets`: `browser_seconds` used matches the run.
4. Open one screenshot through `GET /machine/artifacts/{id}/content` (save to the scratchpad, look at it): it must show the procedure page, not an error or consent wall. Record a short verdict. If most captures are cookie or consent walls, say so in the ledger; that is a finding for the crawlers suite, not something to fix here.
5. Record the pages still without a screenshot (the S0 count after the drain), and the date to repeat (next UTC day), so the owner can schedule the rest.

### Fallback without the route

Only with the owner's say-so, because it can spend browser seconds on pages that were not categorised, and the tool deliberately has no "every snapshot of a host" mode. List the snapshots of the hosts of the 2026-10-30 drain (see the extraction [run-ledger](../extraction/run-ledger.md): `www.arbeitsagentur.de`, `www.ble.de`, `www.bundesarchiv.de`, `www.bzkj.de`, `www.bundesjustizamt.de`) with `artifacts list --host H --kind html_snapshot`, and `POST /machine/tasks` once per page with `{kind: "capture_screenshot", priority: 300, input_key: "shot@1", target_url: <source_url>, catalogue_service_id}`. Prefer waiting one deploy.

### What to write in the ledger

Run IDs (the drain), counts before and after (screenshots, pending, pages missing), browser seconds, bytes, the verdict on one image, and the next date to repeat. Chapter 10 copies the totals into the operator doc and the smoke checklist.

## LR2 — Showcase curation

**Aim.** Production candidates are sparse and unreviewed, so the new pages cannot be judged on them. This run completes a handful of the **highest-ranking** real candidates by hand, so the owner can open fully populated item pages: tags on both axes, ingress and egress cards, the flow diagram, a screenshot. Everything written is marked `manual`.

### Preconditions

1. Chapters [1](chapters/01-capture-requeue.md), [2](chapters/02-completeness-read-model.md), [3](chapters/03-public-candidate-api.md) and [11](chapters/11-manual-curation-tool.md) are merged into the loop branch, LR1 is recorded, and **the owner has deployed the API again** so that `GET $DISCOVERY_API_URL/api/v1/candidates?limit=1` answers 200 (unguarded) and carries the manual override. If it answers 404 the deploy is missing: record the blocker.
2. `probe.env` is sourced, the clean worktree and `PYTHONPATH` are set as in LR1.
3. Today's browser seconds: `budget show --resource browser_seconds` has at least 60 left, or the capture step (C5) is deferred to the next UTC day and recorded as such.

### C0 — Rank and choose

```bash
curl -s "$DISCOVERY_API_URL/api/v1/candidates?sort_by=completeness&sort_order=desc&limit=30" > "$SCRATCH/top.json"
```

Record the top 30 with `completeness` and the five flags (the "before"). Choose **five** candidates (never more than eight) from the top, in rank order, with these exclusions: no candidate without `has_snapshot`; no candidate whose title is a known false positive or generic (`Bescheid`, `Kontaktformular`, `Erforderliche Dokumente`, `weitere Nachweise ...`, an `Anlage N` annex, a login method or a technical file; the false-positive list in the extraction [run-ledger](../extraction/run-ledger.md)); no candidate whose page is a consent wall or login wall. Within what is left, prefer a set that exercises the interface: at least one with ingress **and** egress, one with only ingress, one with only egress, one with many neighbours (aim for more than the diagram cap of 12 on one side only if the page genuinely lists that many; otherwise state that the cap is covered by the unit tests), one with a long title (over 60 characters, for the tooltip), one tagged on both axes with two codes. State for each choice which role it plays in the set. If the ranking offers fewer than five usable candidates, take the best usable ones and say so.

### C1 — Read the pages

For each chosen candidate:

```bash
H="X-API-Key: $DISCOVERY_API_KEY"; B="$DISCOVERY_API_URL/api/v1/discovery/machine"
python -m discovery_ingest candidates page --candidate-id <id> --out "$SCRATCH/pages"
curl -s -H "$H" "$B/taxonomy"     # the closed domain and life-situation vocabulary, with short descriptions
```

`candidates page` prints the procedure(s) (`catalogue_service_id`, `source_url`, screenshot flag) and writes the cleaned text. Read the text. Decide:

- **Tags.** The domain (at most 2) and life-situation (at most 3) codes under which a citizen would file this procedure, from the closed taxonomy only. Write one line of reason.
- **Edges.** Only edges the page states in a sentence: what this document needs (`requires`: Nachweise, Formulare to bring) and which procedure documents it is needed by (`required_by`) when the page says so. Each edge carries a verbatim sentence (at most 300 characters) as its excerpt, and a condition and optional flag when the sentence has them. Neighbours that are already candidates keep their title exactly; a neighbour that is not yet a candidate is added with `"create": true` on the same procedure. **Never invent an edge**; if the page supports none, replace the candidate by the next in rank.

### C2 — Write and review the file

Write `docs/operations/candidate-curation/showcase.json` (schema of chapter 11), then:

```bash
python -m discovery_ingest candidates curate --file docs/operations/candidate-curation/showcase.json --dry-run
```

The dry run validates codes, titles and the grounding of every excerpt against the cleaned page, and prints one line per candidate. Fix every failure by correcting the file; do not use `--no-check-pages` unless the page needs a render, and then say so in the ledger. Commit the file through a small docs PR into the loop branch (branch `docs/candidate-view-showcase`) so the owner can review the curation before or after it is applied; the PR description lists each candidate, its codes and its edges in plain words.

### C3 — Apply

```bash
python -m discovery_ingest candidates curate --file docs/operations/candidate-curation/showcase.json
```

Record the final report line (`mentions_created`, `mentions_updated`, `edges_created`, `edges_updated`, `edges_skipped`, `unknown_codes`). A non-zero `edges_skipped` or `unknown_codes` is a stop: read the reasons, fix the file, re-run (idempotent).

### C4 — Capture the chosen pages first

```bash
python -m discovery_ingest capture requeue --service-id <id> --service-id <id> --limit 20
python -m discovery_ingest worker drain --kinds capture_screenshot --max-tasks 5 --max-batches 6 \
  --time-budget-seconds 300 --browser-budget-seconds 150
```

Only the chosen procedures are queued; if other `capture_screenshot` tasks are pending they are claimed in priority order, so stop the drain early with `--max-tasks` rather than letting it spend the whole day on others. Verify each chosen procedure now has a screenshot (`candidates page` prints the flag). A quota stop defers the rest to the next UTC day: record which candidates still lack one.

### C5 — Verify as the owner will see it

1. `GET /api/v1/candidates?filter[complete]=yes&sort_by=completeness&sort_order=desc`: the chosen candidates appear, `complete` true, tags with names on both axes. Record id, title, completeness and flags (the "after") for each.
2. `GET /api/v1/candidates/<id>` for each: `ingress` and `egress` as designed, `description` and `description_source` present, `screenshot` set.
3. `curl -sI "$DISCOVERY_API_URL/api/v1/candidates/<id>/screenshot"`: 200, `image/*`, `Cache-Control` with `immutable`, an `ETag`; the same request with `If-None-Match` answers 304.
4. Look at one screenshot (save it to the scratchpad and open it): it shows the procedure page, not an error or consent wall. Record a short verdict.
5. Write the showcase list into the ledger (id, title, role in the set, URL path `/candidates/<id>`), so chapter 10's smoke checklist can name them and the owner can open them after the web deploy.

### Stop conditions and reversal

Stop and record a blocker when: the public list answers 404 (deploy missing), the dry run cannot ground an excerpt and the page needs a render, fewer than three usable candidates exist, or the API refuses a write. To undo the whole run the owner runs the SQL in `docs/operations/candidate-view.md` (written by chapter 10): delete `discovery_candidate_edge` rows with `extractor = 'manual'`, then `discovery_candidate_mention` rows with `extractor = 'manual'`, then staged candidates left without a mention. Nothing extracted is touched.

### What to write in the ledger (LR2)

Ranks and flags before and after, the chosen set with each role, the codes and edge counts per candidate, the `curate` report line, the docs PR, the capture result, the verdict on one screenshot, and any candidate still missing a screenshot with the date to finish it.
