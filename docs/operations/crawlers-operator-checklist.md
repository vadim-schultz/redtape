# Crawlers operator checklist

Every manual action of the crawlers suite, in the order it is needed, so no live gate waits for a forgotten console
step. Merging a chapter never waits for a step: the code is tested against fakes. A step unlocks a **live gate**.

Tick the box in the table when a step is done. Write the date and, where a workflow ran, the GitHub Actions run ID in
the same row and in [`run-ledger.md`](../../.plans/crawlers/run-ledger.md). Never paste a secret, a token or an access
key into this file, a commit or a chat. The suite and its known gaps: [loops/crawlers.md](loops/crawlers.md).
Drain and probe behaviour: [discovery-online.md](discovery-online.md) and [scheduled-jobs.md](scheduled-jobs.md).

**Short path after the release deploys:** [crawlers-post-deploy-human-steps.md](crawlers-post-deploy-human-steps.md) lists only the steps a person must do.

## Checklist

| Step | Tick | Date and run ID | What | Needed before |
| --- | --- | --- | --- | --- |
| S1 | [ ] | | Create the private R2 bucket | S3 |
| S2 | [ ] | | Create an R2 API token scoped to the bucket | S3 |
| S3 | [ ] | | Set the `OBJECT_STORE_*` variables in Render | the first upload, S6 |
| S4 | [ ] | | Set the five probe secrets in GitHub | S6 |
| S5 | [ ] | | Confirm the existing configuration | any live gate |
| S6 | [ ] | | Run the storage probe and record the result | chapters 14 to 16 live gates |
| S7 | [ ] | | Verify each chapter's live gate | after the release reaches `main` |
| S8 | [ ] | | Monitor limits (ongoing) | monthly |
| S9 | [ ] | | Rotate, roll back or swap a provider (as needed) | as needed |
| S10 | [ ] | | Review and emit candidates | any bulk emit |
| S11 | [ ] | | Repair mis-recorded fetch tasks | the chapters 2 and 4 live gates |
| S12 | [ ] | | Census queries F1 to F3 | chapters 7 and 12 |
| S12b | [ ] | | Census query F4 | the extraction suite |
| S13 | [ ] | | Enable the schedules | after S14 and the chapter 15 live gate |
| S14 | [ ] | | Re-pend completed fetches so each gets a render task | S13 |
| S15 | [ ] | | Create the Cloudflare browser token, note the account id | S16 |
| S16 | [ ] | | Store the Cloudflare secrets, run the browser probe | chapter 15 |
| S17 | [ ] | | Confirm storage is ready for snapshots | the first render run |
| S18 | [ ] | | Run the browser drain on a laptop (optional) | nothing |
| S19 | [ ] | | Keep Cloudflare on free plans, set billing notifications | the first R2 upload |
| S20 | [ ] | | Compare Actions usage monthly | monthly |
| S21 | [ ] | | Set the budget caps in Render | the first R2 upload |

The suite's release checklist in [`run-ledger.md`](../../.plans/crawlers/run-ledger.md) is complete only when S1 to S6,
S10, S12 to S17 and S19 to S21 are recorded with dates and run IDs. S18 is optional.

## Reported done

The operator reported these steps as done by 2026-10-27. No run ID was recorded for them in this repository, so treat
them as reported rather than verified, and tick them after your own check.

- **S1, S2, S3 and S4.** The R2 bucket, the bucket-scoped token, the Render `OBJECT_STORE_*` variables and the five GitHub probe
  secrets exist. S6 is the proof that they work.
- **S5.** The existing configuration (`DISCOVERY_API_URL`, `DISCOVERY_API_KEY`, `FEDERAL_JURISDICTION_ID`,
  `DISCOVERY_ADMIN_EMAILS`) is in place.
- **S12 and S12b.** The census ran on 2026-10-26 (520 PVOG and 893 GovData rows). The results are in the ledger under
  "Census results" and in the chapter 7 fixtures.
- **S15 and S16.** The Cloudflare token and the two GitHub secrets exist, and the browser probe ran from a laptop. The
  ledger records the partial chapter 15 probe (9 of 21 planned calls, stopped by a rate-limit 429) and the chapter 19
  screenshot probe (4 calls) of 2026-10-27, with about 26 of the 600 daily browser seconds used.
- **S19 and S21.** Cloudflare billing notifications and the ledger caps in Render are set.

## Still open

- **S6.** The storage probe has not passed yet. `gh workflow run discovery-storage-probe.yml` answered **404**: the
  workflow file is not yet on `main`, and a workflow can be dispatched only from the default branch. Run the probe on a
  laptop instead (S6 below).
- **S7.** The live gates of the chapters. They need the release on `main`, and for the render gates S17 and billing.
- **S10.** The first emit of five reviewed candidates.
- **S11.** The repair of the redirected and transport-failed fetch tasks.
- **S13 and S14.** The schedules and the re-pend. Keep both schedule variables unset until then.
- **S17.** Needs the release deployed to Render (so the artifact routes exist) and S3.
- **S18.** Optional laptop drain.
- **S20.** The first monthly comparison, due in the first month after the drains start.
- **S8 and S9** are ongoing duties, not one-time steps.
- **Native review of the German strings** (list at the end of this file).

## Steps

Commands assume a shell in the repository root unless a `cd` says otherwise. A deploy of the release applies the new
migrations and seeds the translations: `apps/api/scripts/start.sh` runs `alembic upgrade head` and the seed scripts on
every boot.

**S1: Create the R2 bucket.** Cloudflare dashboard (the account that hosts the frontend), R2 Object Storage, Create
bucket. Name it `discovery-artifacts`, pick the location hint **Eastern Europe (EEUR)** or the nearest to Render's
Frankfurt region, and storage class **Standard** (the free allowance does not cover Infrequent Access). Keep it
**private**: do not enable the public `r2.dev` URL or a custom domain. The application caps a file at 8 MB and the whole
bucket at `OBJECT_STORE_MAX_BYTES` (S21).

**S2: Create an R2 API token.** R2, Manage API tokens, Create API token, permission **Object Read & Write**, scoped to the
bucket `discovery-artifacts` only. Copy the Access Key ID and the Secret Access Key at once; the secret is shown once.
Note the account id: the S3 endpoint is `https://<account_id>.r2.cloudflarestorage.com` and the region is `auto`. These
keys are server-only. Never put them in the web app, and do not reuse the Browser Run token (S15).

**S3: Render environment.** Render, `redtape-api`, Environment. Add `OBJECT_STORE_ENDPOINT_URL` (the R2 endpoint),
`OBJECT_STORE_REGION` (`auto`), `OBJECT_STORE_BUCKET` (`discovery-artifacts`), `OBJECT_STORE_ACCESS_KEY_ID` and
`OBJECT_STORE_SECRET_ACCESS_KEY`, plus any caps from S21. Redeploy and check `/health`. Never put them in `render.yaml`
(it is committed). Without them the API still boots and the artifact routes answer 503. The Cloudflare browser token is
not a Render variable. Details: [deployment-checklist.md](deployment-checklist.md).

**S4: GitHub secrets for the probe only.** Repository, Settings, Secrets and variables, Actions: add the same five
`OBJECT_STORE_*` names for `discovery-storage-probe.yml`. No other workflow receives them. The existing discovery
secrets stay as they are.

**S5: Confirm the existing configuration.** GitHub secrets `DISCOVERY_API_URL` (host root, no path),
`DISCOVERY_API_KEY` (`rt_...`, key name `discovery-scheduled-gha`) and `FEDERAL_JURISDICTION_ID`; Render
`DISCOVERY_ADMIN_EMAILS`. Check the secret names with `gh secret list`.

**S6: Run the storage probe and record the result.** `gh workflow run <file>` returns 404 for a workflow that is not
yet on `main`, so run the probe on a laptop with the Render values exported. Do not commit the env file.

```bash
cd apps/api && set -a; source <env file>; set +a; .venv/bin/python -m scripts.object_store_probe
```

`<env file>` holds the five `OBJECT_STORE_*` values (the probe also reads `apps/api/.env`). Every step must pass,
including the unauthenticated GET of the presigned URL. The probe prints the recommended checksum variant: the code
ships `when_required`; if only `when_supported` passes, change the default. If the presigned GET fails, record it in
[gaps-and-decisions.md](../../.plans/crawlers/gaps-and-decisions.md): the fallback (reads streamed by the API) changes
chapters 14 and 16. After the release reaches `main`, the same probe runs with
`gh workflow run discovery-storage-probe.yml`; record that run ID too.

**S7: Verify the live gates with `gh`.** After the release is on `main` and deployed. For each gate dispatch the named
workflow, read the report, record the run ID in the ledger.

```bash
gh workflow list
gh workflow run discovery-drain.yml -f kinds=fetch_url -f max_tasks=50 -f max_batches=1
gh run list --workflow=discovery-drain.yml --limit 5
gh run view <run-id> --log
```

| Chapter | Gate |
| --- | --- |
| 2, 3, 4, 5 | After S11: `discovery-drain.yml -f max_batches=3 -f time_budget_seconds=600` ends with `batches` 3 and a numeric `remaining`. Two dispatches show `remaining` falling. A queued third run cancels the older pending one. A browser kind in `discovery-drain.yml` exits 2 (no Cloudflare variables): that refusal is expected |
| 7 | `platform-maintenance.yml -f job=discovery`, then `discovery-drain.yml -f kinds=harvest_payload -f max_batches=5`. Check `GET …/admin/candidates`, the real link keys (`title`, `uri` were assumed), `languageCode` and the noise quality |
| 12 | `discovery-fim-probe.yml -f keys=99154021000000,99070016261000`, then `discovery-drain.yml -f kinds=enrich_metadata -f max_batches=3`. One GovData row shows an entity, claims and stage T3 in the admin pipeline view |
| 13, 14 | S6 passes. The migration `20261027_artifacts` is applied (deploy runs it) |
| 15 | S17 first. `discovery-drain.yml -f kinds=fetch_url`, then `discovery-render.yml -f max_tasks=5 -f max_batches=2 -f time_budget_seconds=300`. An `html_snapshot` appears in the admin artifacts route. Record run IDs, browser seconds per page and pages per run |
| 16, 20 | As an admin: a rendered row's pipeline detail shows the snapshot, its link works within five minutes and fails after expiry; Tasks lists `render_page` with a `login_wall` chip; Coverage shows byte chips and budget meters, including the 80 percent warning; the document detail page shows evidence. Check light and dark, `de` and `en`, 360 px |
| 17 | `discovery-drain.yml -f kinds=extract_page` ends `queue_empty`. `discovery-fixture-capture.yml -f host=verwaltung.bund.de -f limit=5` returns rendered HTML |
| 19 | Needs an extractor or the extraction suite. `discovery-render.yml -f kinds=capture_screenshot -f max_tasks=5 -f max_batches=1`. Record run ID, artifact id, browser seconds, stored bytes. A known login URL completes `login_wall` with no upload |
| 23 | `GET …/machine/budgets` lists five resources with caps. `discovery-drain.yml -f max_batches=1 -f max_tasks=5` logs `budget show` first and reports minutes last (about 1 to 3 minutes of `actions_minutes`) |

**S8: Monitor limits (monthly, or when alerted).** Supabase free plan: 500 MB database; the project goes read-only above
it, and the API soft limit is 400 MB. Cloudflare free plan: R2 10 GB-month, 1 million Class A and 10 million Class B
operations a month, 10 browser minutes a day (Dashboard, Browser Run usage). **R2 bills past its free tier**, so the
ledger caps (S21) and the billing notification (S19) matter more than the dashboard. The admin Coverage screen shows the
same numbers against the caps.

```sql
select pg_size_pretty(pg_database_size(current_database())) as db_size;
```

```sql
select kind, count(*) as artifacts, pg_size_pretty(sum(byte_size)) as bytes
from discovery_artifact group by 1;
```

Act at 80 percent: prune screenshots, lower the snapshot retention, or raise a cap only after checking Cloudflare's usage
page (S19).

**S9: Rotation, rollback and provider swap.**

- Rotate: create a new access key, update Render and the GitHub secrets, redeploy, run S6, then delete the old key. For the
  Cloudflare token, create a new one (S15), replace the `CLOUDFLARE_BROWSER_API_TOKEN` secret, run the browser probe
  (S16), then delete the old token.
- Roll back: unset the Render `OBJECT_STORE_*` variables and redeploy. Artifact routes answer 503, browser drains refuse
  to start (S17), a run in flight releases its tasks and stops `storage_unavailable`, and nothing else breaks. To stop
  rendering without touching storage, delete `DISCOVERY_RENDER_SCHEDULE` and the Cloudflare secrets.
- Swap provider: create the bucket and keys at the new S3 service, change the five variables, run S6. Keys are
  content-addressed, so copy the bucket contents (for example with `rclone`) if history matters.

**S10: Review and emit candidates.**

1. Open `/admin/discovery/documents`, sort by mentions, open a few candidates and read their excerpts and evidence.
2. Dry run: `python -m discovery_ingest candidates emit --all-staged --min-mentions 3 --limit 5 --dry-run`.
3. Emit five: the same command without `--dry-run`. Inspect the pending suggestions through the suggestion API and record
   the counts and ids.
4. Only then emit larger batches (limit at most 50). Never run an unbounded emit. Skips for `duplicate` are expected where
   a document already exists.

**S11: Repair mis-recorded fetch tasks (before the chapters 2 and 4 live gates).** Redirects were recorded as completed;
two transport failures are final. Run the count first.

```sql
select count(*) from discovery_task t
where t.kind = 'fetch_url' and t.status = 'completed'
  and exists (select 1 from discovery_fetch_log f
              where f.discovery_task_id = t.id and f.http_status between 300 and 399);
```

```sql
update discovery_task t
set status = 'pending', claimed_at = null, lease_expires_at = null, last_error = null
where t.kind = 'fetch_url' and t.status = 'completed'
  and exists (select 1 from discovery_fetch_log f
              where f.discovery_task_id = t.id and f.http_status between 300 and 399);
```

```sql
update discovery_task
set status = 'pending', claimed_at = null, lease_expires_at = null, last_error = null
where kind = 'fetch_url' and status = 'failed'
  and (last_error = 'timed out' or last_error like '%Connection reset%');
```

After the retry migration is deployed, add `attempt_count = 0, not_before = null` to both updates.

**S12: Census queries F1 to F3 (done; kept for a repeat).** Paste the outputs into the ledger.

```sql
-- F1: which PVOG modules exist and how many are filled
select m->>'title' as module_title, m->>'code' as code, m->>'xZufiCategory' as category,
       count(*) as total,
       count(*) filter (where m->>'filled' = 'true') as filled,
       count(*) filter (where case when jsonb_typeof(m->'links') = 'array'
                                   then jsonb_array_length(m->'links') else 0 end > 0) as with_links
from catalogue_service c,
     jsonb_array_elements(case when jsonb_typeof(c.raw_payload->'details') = 'array'
                               then c.raw_payload->'details' else '[]'::jsonb end) m
where c.source = 'pvog'
group by 1, 2, 3
order by filled desc, total desc
limit 60;
```

```sql
-- F2: eight filled "Unterlagen" modules
select c.external_id, c.title_i18n->>'de' as procedure, m->>'title' as module_title,
       left(m->>'text', 700) as excerpt, m->'links' as links
from catalogue_service c,
     jsonb_array_elements(case when jsonb_typeof(c.raw_payload->'details') = 'array'
                               then c.raw_payload->'details' else '[]'::jsonb end) m
where c.source = 'pvog' and (m->>'title') ilike '%unterlage%' and m->>'filled' = 'true'
limit 8;
```

```sql
-- F3: key shapes for the FIM probe
(select source, external_id, raw_payload->>'leika_key' as govdata_key, null::jsonb as pvog_keys, portal_url
   from catalogue_service where source = 'govdata' order by random() limit 5)
union all
(select source, external_id, null, raw_payload->'leikakeys', portal_url
   from catalogue_service where source = 'pvog' order by random() limit 5);
```

**S12b: Census F4 (done; for the extraction suite).** Do PVOG and GovData payloads carry Lebenslagen or LeiKa categories
that map to the 18 life-situation codes? The 2026-10-26 result found none, so there is no free static mapping.

```sql
-- F4: which keys in the payloads could carry a life situation
select c.source, k as payload_key, count(*) as rows
from catalogue_service c, jsonb_object_keys(c.raw_payload) k
where k ilike any (array['%lebenslage%', '%leika%', '%categor%', '%thema%', '%tag%'])
group by 1, 2 order by rows desc limit 40;
```

**S13: Enable schedules (variables).** Repository, Settings, Secrets and variables, Actions, Variables. Set
`DISCOVERY_DRAIN_SCHEDULE=enabled` only after S14 is done and the release is deployed (otherwise the backlog is fetched
without enqueuing a render). Set `DISCOVERY_RENDER_SCHEDULE=enabled` only after the chapter 15 live gate and after you
checked the ledger: the render schedule spends about 15 runner minutes a day, the drain allowance is 400 minutes a
month (1,000 minus the 600 CI reserve), and the backlog is about 22 such runs. Prefer a laptop drain (S18) or manual
dispatch. To pause, delete the variable; manual dispatch keeps working.

**S14: Re-pend completed fetches so each gets a render task (after the release is deployed).** About a hundred pages. A
completed task is never enqueued again, so a page fetched before `render_page` existed gets no render until it is
re-pended. Run the count, then the update.

```sql
select count(*) from discovery_task where kind = 'fetch_url' and status = 'completed';
```

```sql
update discovery_task
set status = 'pending', claimed_at = null, lease_expires_at = null, last_error = null
where kind = 'fetch_url' and status = 'completed';
```

Then dispatch `discovery-drain.yml` with `kinds=fetch_url`, then `discovery-render.yml`, and confirm that snapshots
appear.

**S15: Create the Cloudflare browser token and note the account id.** Use the Cloudflare account that hosts the
frontend; the **free plan** is enough (10 browser minutes a day, one request every 10 seconds). Dashboard, copy the
Account ID. My Profile, API Tokens, Create Token, Create Custom Token, permission **Account, Browser Run, Edit** and
nothing else, limited to this account, with no client IP filter (GitHub runners change address). Copy the token once. It
is **not a Render variable** and must never be committed.

**S16: Store the Cloudflare secrets and run the browser probe.** Add the repository secrets `CLOUDFLARE_ACCOUNT_ID` and
`CLOUDFLARE_BROWSER_API_TOKEN` (`gh secret set CLOUDFLARE_BROWSER_API_TOKEN`). Only `discovery-render.yml` and
`discovery-browser-probe.yml` use them. The probe needs only those two variables, so it runs on a laptop:

```bash
python -m discovery_ingest browser probe --url https://example.com --url https://fimportal.de
```

`gh workflow run discovery-browser-probe.yml -f urls="https://example.com,https://fimportal.de"` works once the file is
on `main`. The 2026-10-27 probe stopped after 9 of 21 planned calls (rate-limit 429). When the daily allowance allows,
finish it with
`python -m discovery_ingest browser probe --url https://fimportal.de/detail/L/99155004000000 --variant content-lean --variant snapshot-md --variant screenshot-jpeg --variant screenshot-png --variant snapshot-shot`.
Record the findings in the ledger.

**S17: Confirm storage is ready for snapshots.** Browser drains refuse to start while the status route reports
`storage_enabled: false`, so S1 to S4 and the release must be in place before the first render run. The machine API key
goes in the `X-API-Key` header:

```bash
curl -s -w "\nHTTP %{http_code}\n" -H "X-API-Key: $DISCOVERY_API_KEY" "$DISCOVERY_API_URL/api/v1/discovery/machine/artifacts/status"
```

Expect `HTTP 200` and `"storage_enabled": true`. A 401 means the key or the URL is wrong; a 503 or `false` means the
Render variables (S3) are missing.

**S18: Run the browser drain on a laptop (optional, costs no Actions minutes).** With `DISCOVERY_API_URL`,
`DISCOVERY_API_KEY` and the two Cloudflare variables exported:

```bash
cd apps/discovery-ingest && pip install -e .
python -m discovery_ingest worker drain --kinds render_page --max-tasks 5 --max-batches 40 \
  --time-budget-seconds 900 --browser-budget-seconds 480
```

At most one run a day: the free allowance is 10 browser minutes a day and the budget leaves a margin of about two
minutes. A page takes about 15 seconds (the 11 second gap plus the render), so a 900 second run renders about 55 to 65
pages. A screenshot adds about 1 to 2.5 seconds of browser time and 60 to 300 KB. The report shows
`browser_seconds_used`, `released` and the stop reason.

**S19: Keep Cloudflare on free plans and set billing notifications (before S1 is used).** R2 and Workers AI stay free
only while the account stays on the Workers **Free** plan. Do not upgrade to Workers Paid: Workers AI would then bill
$0.011 per 1,000 neurons, and R2 bills regardless. Dashboard, Notifications: add a usage-based billing alert and, if
offered, R2 storage and operation alerts at 80 percent of the free allowance. Record the plan name and the alert ids in
the ledger. This is the only guard that sees what the application cannot.

**S20: Compare Actions usage monthly.** GitHub, Settings, Billing and plans, Usage for Actions. Compare the
repository's minutes with the ledger resource `actions_minutes` (`python -m discovery_ingest budget show`). The cap is
1,000 minutes a month for this repository, with a 600 minute CI reserve. If CI alone approaches the reserve, lower the
drain allowance, not the other way round. Record the month, the GitHub figure and the ledger figure.

**S21: Set the budget caps (Render).** Variables on `redtape-api`: `OBJECT_STORE_MAX_BYTES` (default 8 GiB),
`BUDGET_R2_CLASS_A_MONTHLY` (400000), `BUDGET_R2_CLASS_B_MONTHLY` (4000000), `BUDGET_BROWSER_SECONDS_DAILY` (480),
`BUDGET_ACTIONS_MINUTES_MONTHLY` (1000), `ACTIONS_CI_RESERVE_MINUTES` (600) and `DB_SOFT_LIMIT_BYTES` (400000000). The
defaults are already below the allowances, so set a variable only to tighten it or to tune it after the first month.
Check with `GET /api/v1/discovery/machine/budgets`. The extraction suite adds `BUDGET_NEURONS_DAILY`.

## German strings that need native review

A language model wrote the German copy of the admin screens of chapters 8, 10, 16 and 20 (the English text is the
reference). Have a native speaker review each key in
[`apps/api/scripts/seed_data/translations/de.json`](../../apps/api/scripts/seed_data/translations/de.json). The web
fallback in `apps/web` must stay identical to the seed, so change both in one commit.

**Chapter 8 (task and coverage screens)** (11 keys)

`discovery_admin.coverage.candidate_mentions`, `discovery_admin.coverage.candidates_emitted`, `discovery_admin.coverage.candidates_staged`, `discovery_admin.coverage.candidates_total`, `discovery_admin.coverage.kind_chip`, `discovery_admin.tasks.col_attempts`, `discovery_admin.tasks.col_kind`, `discovery_admin.tasks.col_retry`, `discovery_admin.tasks.filter_kind`, `discovery_admin.tasks.filter_kind_all`, `discovery_admin.tasks.retry_none`

**Chapter 10 (Documents list and paging)** (27 keys)

`discovery_admin.documents.col_first_seen`, `discovery_admin.documents.col_jurisdiction`, `discovery_admin.documents.col_mentions`, `discovery_admin.documents.col_roles`, `discovery_admin.documents.col_status`, `discovery_admin.documents.col_title`, `discovery_admin.documents.count_one`, `discovery_admin.documents.count_other`, `discovery_admin.documents.empty_description`, `discovery_admin.documents.empty_title`, `discovery_admin.documents.filter_min_mentions`, `discovery_admin.documents.filter_role`, `discovery_admin.documents.filter_search`, `discovery_admin.documents.filter_sort`, `discovery_admin.documents.filter_source`, `discovery_admin.documents.min_mentions_any`, `discovery_admin.documents.min_mentions_option`, `discovery_admin.documents.role_all`, `discovery_admin.documents.role_form`, `discovery_admin.documents.role_required`, `discovery_admin.documents.sort_mentions_desc`, `discovery_admin.documents.sort_newest`, `discovery_admin.documents.sort_title_asc`, `discovery_admin.documents.source_all`, `discovery_admin.pagination.next`, `discovery_admin.pagination.previous`, `discovery_admin.pagination.range`

**Chapter 16 (Artifacts panel, budgets, result notes)** (26 keys)

`discovery_admin.artifacts.budget_actions_minutes`, `discovery_admin.artifacts.budget_browser_seconds`, `discovery_admin.artifacts.budget_exhausted`, `discovery_admin.artifacts.budget_neurons`, `discovery_admin.artifacts.budget_r2_class_a`, `discovery_admin.artifacts.budget_r2_class_b`, `discovery_admin.artifacts.budget_stored_bytes`, `discovery_admin.artifacts.budget_usage`, `discovery_admin.artifacts.budgets_error`, `discovery_admin.artifacts.budgets_title`, `discovery_admin.artifacts.chip_kind`, `discovery_admin.artifacts.chip_total`, `discovery_admin.artifacts.chip_total_warning`, `discovery_admin.artifacts.download`, `discovery_admin.artifacts.empty`, `discovery_admin.artifacts.html_meta`, `discovery_admin.artifacts.kind_html_snapshot`, `discovery_admin.artifacts.kind_screenshot`, `discovery_admin.artifacts.link_unavailable`, `discovery_admin.artifacts.screenshot_alt`, `discovery_admin.artifacts.storage_unconfigured`, `discovery_admin.artifacts.title`, `discovery_admin.tasks.note_login_wall`, `discovery_admin.tasks.note_no_extractor`, `discovery_admin.tasks.note_no_mentions`, `discovery_admin.tasks.note_oversize`

**Chapter 20 (document detail, mentions)** (10 keys)

`discovery_admin.document.col_excerpt`, `discovery_admin.document.col_extractor`, `discovery_admin.document.col_field`, `discovery_admin.document.col_host`, `discovery_admin.document.col_procedure`, `discovery_admin.document.col_role`, `discovery_admin.document.jurisdiction`, `discovery_admin.document.mentions_empty`, `discovery_admin.document.mentions_title`, `discovery_admin.document.official_url`

**Chapter 20 (emit preview and suggestion state)** (14 keys)

`discovery_admin.document.emit_cli_hint`, `discovery_admin.document.emit_conflicts`, `discovery_admin.document.emit_emitted`, `discovery_admin.document.emit_official_url`, `discovery_admin.document.emit_pending`, `discovery_admin.document.emit_skipped`, `discovery_admin.document.emit_source_url`, `discovery_admin.document.emit_title`, `discovery_admin.document.emit_title_label`, `discovery_admin.document.emit_would_create`, `discovery_admin.document.skip_reason_duplicate`, `discovery_admin.document.skip_reason_invalid_payload`, `discovery_admin.document.skip_reason_no_mentions`, `discovery_admin.document.skip_reason_no_source_url`

