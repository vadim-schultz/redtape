# Search-first — remaining work and operator runbook

**Written:** 2026-11-11 · **Suite:** [00-architecture.md](00-architecture.md) · [01-rollout.md](01-rollout.md) · [run-ledger.md](run-ledger.md) · [gaps-and-decisions.md](gaps-and-decisions.md)

This file says what is left after chapters C1–C17 and C11 were merged and released to `main`, who does each step, and the exact commands. It is written to be followed from a laptop that can reach the production Supabase database directly (the main workstation's network cannot; the Render shell is a paid option and is not used; no GitHub Actions workflow is used to reach the database).

## 1. Where things stand

| Area | State |
| --- | --- |
| Code | C1–C17 and C11 merged and released to `main` (release PR #402, locales PR #404, ledger PRs #403 and earlier). Render redeployed successfully; migrations `20261110_search_schema` and `20261111_translation_schema` ran; `vector` and `unaccent` are enabled on Supabase. |
| Production data | Both work queues are empty and nothing is translated (`embed summary` all zeros; `translate summary` lists `en tr ru uk pl ro` with 0 translated). `candidate_search_text` and `candidate_embedding` are not backfilled yet. |
| Flags | `SEARCH_HYBRID_ENABLED` is off (legacy title-match search is live). Drains are not scheduled (`DISCOVERY_EMBED_SCHEDULE`, `DISCOVERY_TRANSLATE_SCHEDULE` unset). |
| Locales | `ru`, `tr`, `uk`, `pl`, `ro` have UI strings and taxonomy labels seeded on every Render start (`scripts/start.sh` runs `seed_i18n` and `seed_taxonomy`) but are **disabled** and `machine` (unreviewed). `tr`, `uk`, `pl`, `ro` were authored by Claude Code, `ru` by the Workers AI pipeline with its plural forms corrected by Claude Code. Native review is owned by the user. |
| Secrets | Cloudflare token and account id are set on Render and GitHub; the R2 variables are set on Render. |
| Open problem | Workers AI refused calls with `4006` while the dashboard's "today" counter read 7.33k of 10k. Working explanation: Cloudflare enforces a rolling 24-hour window (see section 9). Until it clears, nothing that spends neurons can run. |
| Not built yet | C18's code: golden query set, `apps/api/scripts/search_eval.py`, tuning, `docs/operations/search.md`, `docs/operations/translation-engines.md`, the STATUS update. Claude can do these without production access (section 10). |

Everything ships dark. Rollback for each switch is in section 12.

## 2. Who does what

- **You (other laptop, Cloudflare, Render, GitHub):** sections 3 to 9 and the flag flips in section 11.
- **Claude (this repository, no production access):** the C18 code and docs (section 10), recording evidence in the run ledger, any code fix the steps below turn up. Paste each script's output into the conversation and Claude records it in [run-ledger.md](run-ledger.md).

## 3. Prerequisites on the laptop

1. `git pull` `main`. Install `uv` (and Python 3.12 or the version in `apps/api/pyproject.toml`).
2. In `apps/api`, create `.env` (never commit it; it is gitignored) with the production values from Render:

   ```text
   DATABASE_URL=postgresql+psycopg://postgres.<project_ref>:<password>@aws-0-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require
   ```

   Use the same Session-pooler URL that Render has. Only `DATABASE_URL` is needed for sections 4 and 6. Sections 5 (translation locale list) and 8 (R2) add variables, named where they are needed.
3. Check the connection and the baseline (read-only):

   ```bash
   cd apps/api
   uv sync
   uv run python - <<'EOF'
   from sqlalchemy import text
   from app.db import SessionLocal
   with SessionLocal() as s:
       print("size", s.execute(text("select pg_size_pretty(pg_database_size(current_database()))")).scalar())
       print("candidates", s.execute(text("select count(*) from discovery_document_candidate")).scalar())
       print("alembic", s.execute(text("select version_num from alembic_version")).scalar())
   EOF
   ```

   Expect `alembic 20261111_translation_schema` and a size near the 83 MB baseline (soft limit `DB_SOFT_LIMIT_BYTES` = 475,000,000). Paste the output to Claude: it fills the baseline row in the ledger.
4. The scripts write to production. They are idempotent and resumable, commit per batch and stop cleanly at the database soft limit, so an interrupted run is safe to repeat. Do not run two backfills at the same time.
5. For the queue summaries and drains (any machine with `gh`): `DISCOVERY_API_URL` and `DISCOVERY_API_KEY` for `uv run python -m discovery_ingest embed summary` (run in `apps/discovery-ingest`). On the laptop `uv run` will not rewrite `uv.lock` to a corporate mirror; if `git status` shows `uv.lock` changed, `git checkout apps/discovery-ingest/uv.lock`.

## 4. Backfill A: German search text and embedding tasks (no neurons)

```bash
cd apps/api
uv run python -m scripts.backfill_search
```

It walks every candidate in batches, builds the German `candidate_search_text` row (text, two tsvectors, content hash) and enqueues one embedding task per candidate (the embedding model is from `EMBEDDING_MODEL`, default as in `app/config.py`). Flags: `--batch-size N`, `--after <candidate-uuid>` (resume after the last id the previous run printed). A second run changes nothing. It prints one report (counts, text length stats, the stop reason `finished` or the soft-limit message). Paste it to Claude.

Check afterwards (read-only):

```sql
select locale, count(*) from candidate_search_text group by 1;      -- de = candidate count
select status, count(*) from embedding_task group by 1;             -- pending = candidate count
select pg_size_pretty(pg_database_size(current_database()));
```

Also from the API side: `embed summary` should show `pending_ready` equal to the candidate count.

## 5. Decision needed first for translations: which locales (O-decision, user)

`TRANSLATION_TARGET_LOCALES` defaults to `en tr ru uk pl ro` (all six). All six would take about 337k neurons (about 35 days at the daily share) because the cost is about 10 to 13 neurons per card and locale. The drain works in priority order (high-confidence candidates first, all locales of a candidate together), so a partial run still leaves the best candidates complete. For the PoC, narrowing to two or three locales gets a convincing result much sooner.

Set the chosen list **on Render** (it scopes which tasks the machine API will hand out) and use the **same list** in the laptop environment for section 6 (`TRANSLATION_TARGET_LOCALES="tr uk"` in the shell or in `apps/api/.env`). Azure Translator (open item O17) replaces the engine later through `TRANSLATION_ENGINE`; nothing here has to change for it.

## 6. Embedding drain (needs neurons; after the Cloudflare allowance clears)

Do this only after section 9's check succeeds, otherwise the drain stops with `llm_quota` immediately (harmless, but it flags the day as exhausted).

```bash
gh workflow run discovery-embed.yml          # inputs optional: max_tasks (50), max_batches (60), time_budget_seconds (600), neuron_budget (3000)
gh run watch                                  # then open the run and read the JSON DrainReport
```

A manual dispatch runs regardless of the schedule variable. The drain claims batches of up to 50, embeds with Workers AI, settles against the neuron ledger and stops with one of `queue_empty`, `batch_limit`, `time_budget`, `llm_budget`, `llm_quota`, `db_limit`, `error`. Repeat dispatches until `embed summary` shows `pending_ready` 0 (the German corpus is a few thousand short texts; the cost is an estimate of a few thousand neurons in total, not yet measured). Record the first report, neurons and minutes per run (Actions → run duration).

When the first run is healthy, enable the schedule: `gh variable set DISCOVERY_EMBED_SCHEDULE --body enabled` (cron `10 6,18 * * *`). Keep `EMBEDDING_MODEL` identical on Render and in the workers.

## 7. Backfill B and the translate drain

```bash
cd apps/api
TRANSLATION_TARGET_LOCALES="tr uk" uv run python -m scripts.backfill_translations          # or: --locale tr
```

This only enqueues tasks for missing or stale translations (no neurons). Flags `--batch-size`, `--after`, `--locale`. Check with `translate summary` (`pending_ready` per locale). Then, with the allowance clear:

```bash
gh workflow run discovery-translate.yml      # same inputs as the embed workflow; run cap 2500 neurons, floor 1000 for query embedding
gh run watch
```

Record the first `DrainReport` (claimed, stored, stale, rejected, neurons), the validator failure and repair rate `(repaired + invalid) / units`, the Actions minutes per run and translated / total per locale. Then enable the schedule: `gh variable set DISCOVERY_TRANSLATE_SCHEDULE --body enabled` (daily `10 17 * * *`). Optional variables: `TRANSLATION_ENGINE` (default `llm`), `QUERY_EMBED_RESERVE` (default 1000).

Expect coverage to grow slowly on the free tier (a few hundred cards per day for the whole run cap); that is by design until the Azure engine is in place.

## 8. Backfill C: search text and vectors for translated locales

A stored translation becomes keyword-searchable as soon as it is stored (a subscriber builds its search text). This backfill reconciles anything the subscriber missed and queues the embedding tasks of translations stored earlier. It reads the stored objects from R2, so the laptop also needs the five object-store variables (values from Render):

```text
OBJECT_STORE_ENDPOINT_URL  OBJECT_STORE_REGION (auto)  OBJECT_STORE_BUCKET
OBJECT_STORE_ACCESS_KEY_ID  OBJECT_STORE_SECRET_ACCESS_KEY
```

```bash
cd apps/api
uv run python -m scripts.backfill_search --locale tr --locale uk      # repeatable; same --after/--batch-size
```

One report per locale; a missing or invalid object is reported and skipped; it stops cleanly on the database soft limit or an object-store refusal. Then run the embed drain again (section 6) to embed those texts, and record per-locale search-text rows, embedded and stale counts, and table and index sizes against the budget. `EMBEDDING_LOCALES` (default all seven) gates which locales get embedding tasks; to drop a locale remove it from the setting on Render first, then `uv run python -m scripts.prune_embeddings --locale <code>` (it prints the vector bytes reclaimed; the table and HNSW index only give space back after a vacuum). Decision O10 (which locales keep vectors) is settled by the evaluation in section 10.

## 9. Neuron allowance: confirm and then fix (blocks sections 6 and 7)

1. **Check it has cleared.** The Cloudflare dashboard (Workers AI) shows usage; or one embedding call of a single character costs about 0.001 neuron and returns `4006` while the allowance is refused (any HTTP client with the Workers AI token). Working explanation: the allowance is enforced on a rolling 24 hours, so it frees up as the 2026-11-10 probe spend (about 3.8k neurons) ages out; if it is still refused at the next UTC midnight, the explanation is wrong and Claude should look again. Record the result in the ledger section "Neuron allowance investigation".
2. **Calibrate once it clears.** Run one small known batch through the ledger path and compare the ledger delta, the raw response `usage` fields and the dashboard delta. Claude can then decide whether `translation/metered.py` needs a change (it refunds the whole reservation on a timeout or 5xx and keeps only the estimate for an unusable answer).
3. **Follow-up item (Claude, small chapter):** make the neuron ledger rolling-aware (hourly buckets summed over the trailing 24 hours), because the UTC-day ledger cannot guarantee the 1,000-neuron query-embedding floor if Cloudflare's window is rolling. Until then: never spend outside the ledger (no ad-hoc probes), keep the shipped cadences, and do not raise `BUDGET_NEURONS_DAILY`.

## 10. Chapter 18: evaluation, tuning and the decision to enable hybrid search

Specification: [chapters/18-evaluation-tuning-and-rollout.md](chapters/18-evaluation-tuning-and-rollout.md). Nothing of it exists yet.

**Claude can do now (no production access needed):**

1. Golden query set under `apps/api/tests/fixtures/search_eval/`: at least 20 queries per locale (`de en tr ru uk pl ro`) with expected candidate keys, including cross-lingual cases; non-German queries are flagged machine-written until native speakers review them.
2. `apps/api/scripts/search_eval.py`: keyword only, vector only, fused and combined, each with and without translated rows; recall@10, MRR, nDCG@10 per configuration and locale, mean confidence of the top 10, p50 and p95 latency; real embedder if a token is present, otherwise a recorded-vector cache so CI spends no neurons.
3. Tuning grid on a fixture database: `SEARCH_CONFIDENCE_WEIGHT` in {0, 0.15, 0.3, 0.5, 1}, `RRF_K` in {20, 60, 100}, similarity cut-off, `SEARCH_TOP_N` in {20, 50, 100}, HNSW `ef_search` (and `m`/`ef_construction` if recall needs it).
4. Docs: `docs/operations/search.md`, `docs/operations/translation-engines.md`, `scheduled-jobs.md`, `docs/planning/STATUS.md`; decisions O7, O9, O10, O14 into `gaps-and-decisions.md`.

**Needs production data and you:**

5. Run the evaluation against the real corpus after sections 4 to 8 have populated it (the chapter also wants the screenshots redone with real data; the C9, C10 and C17 images were taken against stubbed or synthetic data and the C9 and C10 images were lost).
6. The gate to enable `SEARCH_HYBRID_ENABLED=true`: on German queries hybrid recall@10 and MRR at least keyword's; no other locale below its keyword baseline; translated rows do not harm; p95 latency within the recorded budget; the keyword fallback verified (remove the embedder token: HTTP 200 with `search_mode: "keyword"`).

## 11. Order of the whole rollout

1. Section 3 (prerequisites) and section 4 (backfill A).
2. Section 9 step 1 (allowance has cleared), then section 6 (embed drain until the queue is empty), then enable `DISCOVERY_EMBED_SCHEDULE`.
3. Section 5 (decide locales, set Render), section 7 (backfill B, translate drain, enable `DISCOVERY_TRANSLATE_SCHEDULE`).
4. Section 8 (backfill C, embed again) as translated rows accumulate.
5. Section 10 items 1 to 4 can run in parallel with all of the above (Claude).
6. Evaluation on real data (section 10 item 5), tuning, record decisions.
7. Native-speaker review per locale: set that locale's entry in `apps/api/scripts/seed_data/translations/review.json` to `reviewed` with `reviewed_by` and `reviewed_on` (a PR to `main`; Render reads it on its next start, and the laptop must `git pull` it because `enable_locale` reads the manifest from the checkout it runs in), then enable one at a time: `cd apps/api && uv run python -m scripts.enable_locale <code>` (refuses machine-only or incomplete locales and says why). Review the glossary and allow-list entries too (`discovery_ingest/translation/glossary_data/`, `discovery_ingest/i18n/data/unchanged.json`; the `ro` `Extractor` entry and the `Anmeldung` rendering as "registration" are the known judgement calls).
8. Set `SEARCH_HYBRID_ENABLED=true` on Render once the gate in section 10 item 6 holds. Run the read-only live validation table in [run-ledger.md](run-ledger.md) ("Post-deploy validation") and record each row.
9. Watch database size, the neuron ledger and Actions minutes for a week.

## 12. Switches and rollback

| Switch | Where | Effect, and how to undo |
| --- | --- | --- |
| `SEARCH_HYBRID_ENABLED` | Render | `false` returns legacy title-match search with no deploy. |
| `SEARCH_CONFIDENCE_WEIGHT` | Render | Default 0.3; `0` is pure relevance, `1` restores confidence-first ordering within the relevance gate. |
| `TRANSLATION_TARGET_LOCALES` | Render and laptop | Narrow or empty list stops claiming; reads are by locale, stored objects and index rows stay (additive, harmless). |
| `EMBEDDING_LOCALES` | Render | Gates enqueue only; drop a locale, then `prune_embeddings.py`. |
| `TRANSLATION_ENGINE` | GitHub variable | Selects the engine for new and stale units only. |
| `DISCOVERY_EMBED_SCHEDULE`, `DISCOVERY_TRANSLATE_SCHEDULE` | GitHub variables | `enabled` turns the cron on; a manual dispatch always runs. Unset to stop. |
| `supported_locale.enabled` | Database via `enable_locale.py` | A locale is hidden again by setting `enabled = false`. |
| `QUERY_EMBED_RESERVE` | GitHub variable | Neurons the translate drain leaves for query embedding (default 1000). |
| `BUDGET_NEURONS_DAILY` | Render | Daily neuron cap of the ledger (default 9,500). Do not raise it (section 9). |

## 13. Housekeeping

- `~/.local/share/redtape/c11-partial-locales/` (the abandoned Workers AI partial output) and the local branch `wip/c15-prior-attempt` can be deleted.
- No credentials are stored in the repository. `apps/api/.env` and `apps/discovery-ingest/.env` stay local.
- Open follow-ups recorded in the ledger and not yet scheduled: the rolling-aware neuron ledger (section 9), a neutral `band_*` copy key for the similarity ring (C10), the missing `ru` and German-length screenshot checks (C9, C10, C17), the `mypy .` errors in `apps/discovery-ingest/tests/` that the chapter 15 verification block reports (CI runs `mypy discovery_ingest`, which is clean), and the unverified incidents from chapters 13 and 12 (a stray `pytest` run once followed the `apps/api/.env` symlink to an unreachable database; nothing is known to have been created outside Alembic).
