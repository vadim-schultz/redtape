---
name: "Chapter 22 — Operator manual steps"
overview: "Everything the operator must do by hand: create the Supabase bucket and keys, set secrets, variables and environment, run repairs and census queries, enable schedules, and monitor limits."
todos:
  - id: checklist
    content: "Publish the numbered checklist with commands and SQL"
    status: pending
  - id: ledger
    content: "Operator records each step, date and run ID in the ledger"
    status: pending
isProject: false
---

# Chapter 22 — Operator manual steps

**Repo:** `redtape` (`docs/operations`) · **Branch:** `docs/crawlers-operator-steps` · **Status:** planned

**Depends on:** [21](21-docs-sync.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/crawlers`

## Goal

Collect every manual action in one place, in the order it is needed, so no chapter is blocked by a forgotten console step. The checklist is copied into `docs/operations/` (a new `crawlers-operator-checklist.md` linked from the runbooks) and each step is ticked with a date and, where relevant, a GitHub Actions run ID.

Merging a chapter never waits for a step: code is tested against fakes in CI. Steps unlock **live gates**.

## When each step is needed

| Step | Needed before |
| --- | --- |
| S12 census | chapter 7 starts (module selection), chapter 12 (F3) |
| S11 repair | chapter 2 live gate, chapter 4 live gate |
| S1–S4, S6 | chapter 13 live gate; ideally before chapter 13 merges |
| S14 re-pend, then S13 | chapter 15 live gate; the scheduled drain must not run before S14 |
| S10 emit routine | after chapter 11 |
| S13 capture schedule | after chapter 19 live gate |
| S5, S7, S8, S9 | ongoing |

## Steps

**S1 — Create the Storage bucket.** Supabase dashboard → Storage → New bucket. Name it `discovery-artifacts`. Keep it **private** (not public). Leave the per-bucket file size limit at or below the global limit (the free plan allows 50 MB per file; the application caps at 8 MB).

**S2 — Create S3 access keys.** Dashboard → Project Settings → Storage → S3 Connection. Note the endpoint (form `https://<project_ref>.storage.supabase.co/storage/v1/s3`) and the region of the project. Create a new access key; copy the Access Key ID and Secret Access Key immediately. These keys are server-only and bypass row-level security. Never put them in the web app.

**S3 — Render environment.** Render → `redtape-api` → Environment. Add `OBJECT_STORE_ENDPOINT_URL`, `OBJECT_STORE_REGION`, `OBJECT_STORE_BUCKET` (`discovery-artifacts`), `OBJECT_STORE_ACCESS_KEY_ID`, `OBJECT_STORE_SECRET_ACCESS_KEY`. Redeploy and check `/health`. Do not put these in `render.yaml` (it is committed). Without them the API still boots and artifact routes return 503.

**S4 — GitHub secrets for the probe only.** Repository → Settings → Secrets and variables → Actions → add the same five names for `discovery-storage-probe.yml`. No other workflow receives them. Existing discovery secrets stay as they are.

**S5 — Confirm existing configuration.** `DISCOVERY_API_URL` (host root, no path), `DISCOVERY_API_KEY` (`rt_...`, name `discovery-scheduled-gha`), `FEDERAL_JURISDICTION_ID` (GitHub secrets); `DISCOVERY_ADMIN_EMAILS` (Render). Check with `gh secret list`.

**S6 — Run the storage probe and record the result.**

```bash
gh workflow run discovery-storage-probe.yml
gh run watch && gh run view --log
```

Every step must pass, including the unauthenticated GET of the presigned URL. Record the run ID and the recommended checksum variant in the ledger.

**S7 — Verify live gates with `gh`.** For each chapter's live gate: dispatch the named workflow, read the report, record the run ID.

```bash
gh workflow list
gh workflow run discovery-drain.yml -f kinds=fetch_url -f max_tasks=50 -f max_batches=1
gh run list --workflow=discovery-drain.yml --limit 5
gh run view <run-id> --log
```

**S8 — Monitor limits (monthly, or when alerted).** Free plan: 500 MB database, 1 GB file storage, 5 GB egress, 50 MB per file. Supabase puts a project into read-only mode when the database limit is exceeded, so check the database as well as storage.

```sql
select pg_size_pretty(pg_database_size(current_database())) as db_size;
```
```sql
select kind, count(*) as artifacts, pg_size_pretty(sum(byte_size)) as bytes
from discovery_artifact group by 1;
```

The admin Coverage screen shows the same artifact totals. Act at 80 percent: prune screenshots, or move to R2 (S9).

**S9 — Rotation, rollback and provider swap.**

- Rotate: create a new access key, update Render and the GitHub secrets, redeploy, run S6, then delete the old key.
- Roll back: unset the Render `OBJECT_STORE_*` variables and redeploy. Artifact routes answer 503, workers skip snapshots and report `snapshot_skipped`, and nothing else breaks.
- Swap to Cloudflare R2: create the bucket and an S3 API token, change the five variables (endpoint `https://<account>.r2.cloudflarestorage.com`, region `auto`), run S6. Existing keys are content-addressed; copy the bucket contents with `rclone` if history matters.

**S10 — Review and emit candidates (after chapter 11).**

1. Open `/admin/discovery/documents`, sort by mentions, open a few candidates and read their excerpts and evidence.
2. Dry run: `python -m discovery_ingest candidates emit --all-staged --min-mentions 3 --limit 5 --dry-run`.
3. Emit five: the same command without `--dry-run`. Inspect the pending suggestions through the suggestion API and record counts and ids.
4. Only then emit larger batches (limit at most 50). Never run an unbounded emit. Skips for `duplicate` are expected where a document already exists.

**S11 — Repair mis-recorded fetch tasks (for chapters 2 and 4).** Redirects were recorded as completed; two transport failures are final. Dry run first.

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

After chapter 4 is deployed, add `attempt_count = 0, not_before = null` to both updates.

**S12 — Census queries (before chapter 7 and chapter 12).** Paste the outputs into the ledger.

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

**S13 — Enable schedules (variables).** Repository → Settings → Secrets and variables → Actions → Variables. Set `DISCOVERY_DRAIN_SCHEDULE=enabled` only after S14 and the chapter 15 live gate (otherwise the backlog is fetched without snapshots). Set `DISCOVERY_CAPTURE_SCHEDULE=enabled` after the chapter 19 live gate. To pause, delete the variable; manual dispatch keeps working.

**S14 — Re-pend completed fetches so snapshots are captured (after chapter 15 deploys).** About a hundred pages; the fetcher is polite (per-host interval). Dry run, then update.

```sql
select count(*) from discovery_task where kind = 'fetch_url' and status = 'completed';
```
```sql
update discovery_task
set status = 'pending', claimed_at = null, lease_expires_at = null, last_error = null
where kind = 'fetch_url' and status = 'completed';
```

Then dispatch `discovery-drain.yml` with `kinds=fetch_url` and confirm snapshots appear (chapter 15 live gate).

## Verification

The operator ticks each step in the checklist document and the ledger. The suite's release checklist in [../run-ledger.md](../run-ledger.md) is complete only when S1–S6, S10 and S12–S14 are recorded with dates and run IDs.

## Out of scope

Automating console steps, infrastructure as code for Supabase, alerting integrations.
