# Extraction — Run ledger

**Loop branch:** `feat/extraction`
**Release branch:** `main`
**Release PR:** not opened.
**CI policy (owner, 2026-10-28):** GitHub Actions minutes are exhausted until the end of October. Chapters gate on the full local CI and merge into the loop branch without remote CI. Rerun remote CI on the release PR if minutes are back.

Update this ledger after every chapter implementation or documented operator verification. A chapter is not complete until its gate, its live gate (or the reason it is deferred), and its refactor outcome are recorded. Record GitHub Actions run IDs, or the local command and date, for every live gate, and the `neurons_used` of every model run.

| Chapter | Plan | Status | Verification | Refactor outcome | Live gate (run ID) | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | [Staging groundwork](chapters/01-staging-groundwork.md) | merged into `feat/extraction` ([PR #223](https://github.com/vadim-schultz/redtape/pull/223)) | Local gate 2026-10-28: api ruff, mypy, 963 tests; migration `20261029_staging_edges` round trip (up, down, up) and `alembic check` clean on a scratch database. Remote Actions did not run (billing). | Row builders moved to `mention_rows.py` and `edge_rows.py`, code filter to `candidate_codes.py`, tag adapter to `candidate_tags.py`. | n/a until deployed | **Operator actions pending:** apply the migration to Supabase/Render; then `GET /machine/taxonomy` returns 13 domains and 18 situations and candidate detail shows empty suggested codes. For E6/E8: mentions response has `unknown_codes`; edge batch response is `{edges_created, edges_updated, edges_skipped, skipped}`; `suggested_*_codes` are `{code, procedures, share, accepted}`; settings `discovery_tag_min_procedures` 2, `discovery_tag_min_share` 0.5. |
| E2 | [Page cleaner](chapters/02-page-cleaner.md) | planned | | | | |
| E3 | [Extraction schema, prompt and grounding](chapters/03-extraction-schema-and-grounding.md) | planned | | | | |
| E4 | [Workers AI client, neuron meter and probe](chapters/04-workers-ai-client-and-probe.md) | planned | | | | |
| E5 | [Eval harness and model choice](chapters/05-eval-harness-and-model-choice.md) | planned | | | | |
| E6 | [llm_extract handler](chapters/06-llm-extract-handler.md) | planned | | | | |
| E7 | [Wiring and workflow](chapters/07-wiring-and-workflow.md) | planned | | | | |
| E8 | [Admin display](chapters/08-admin-display.md) | planned | | | | |
| E9 | [Docs sync and operator steps](chapters/09-docs-and-operator-steps.md) | planned | | | | |
| E10 | [Robots rules fix](chapters/10-robots-rules-fix.md) (executes second) | merged into `feat/extraction` ([PR #222](https://github.com/vadim-schultz/redtape/pull/222)) | Local gate 2026-10-28: ingest ruff, mypy, 494 tests (437 before). Remote Actions did not run (billing); Cloudflare `Workers Builds: redtape-web` check failed on the PR, not investigated (web untouched). | Loops A and B extracted helpers (`_records`, `_groups`, `_lines`); loop C nothing needed. | n/a | Also fixed: a 4xx robots.txt body is no longer parsed as rules. **Operator actions pending:** before/after re-pend counts, local `fetch_url` drain, confirm `dipul.de` still blocked. | Found 2026-10-28: `urllib.robotparser` is first-match and ignores `*` and `$`. Record the re-pend counts before and after. |
| E11 | [Free-tier caps at 95 percent](chapters/11-free-tier-caps-95.md) (executes first) | merged into `feat/extraction` ([PR #221](https://github.com/vadim-schultz/redtape/pull/221)) | Local gate 2026-10-28: api ruff, mypy, 921 tests; ingest ruff, mypy, 437 tests. Remote CI did not run (GitHub Actions minutes exhausted until month end); merged on local CI by owner decision. | Audited, nothing needed. | n/a (config only) | Owner decision 2026-10-28. Record the Render overrides removed, the values the budgets route returns, and the database size headroom. **Operator actions pending:** Render env overrides, budgets route (expect 950000 / 9500000 / 570 / 9500, `actions_minutes` 400), artifacts status `bytes_cap` 9500000000, `pg_database_size` vs 475 MB. |

## Release checklist

- [ ] Staging groundwork is deployed: `issued` role, mention columns, edge table, taxonomy route, tag aggregate (E1).
- [ ] The cleaner meets its recall gate on the fixtures (E2).
- [ ] Schema, prompt version and grounding are tested against canned model outputs (E3).
- [ ] The six internal caps sit at 95 percent of their free allowances, Render overrides are cleared, and the budgets route shows the new values (E11).
- [ ] robots.txt verdicts follow RFC 9309 (longest match, `*`, `$`), the real-file fixtures pass, and the robots failures were re-pended once with counts recorded (E10).
- [ ] The Workers AI probe is recorded: response shape, usage fields, accepted models, neurons per page, reasoning overhead, quota error body (E4).
- [ ] The eval chose a model and prompt version, with precision, recall, grounded rate and tag agreement recorded (E5).
- [ ] `llm_extract` completes tasks, releases on quota or budget, and never fails a page because of a limit (E6).
- [ ] One live run produced candidates, edges and tag suggestions, stayed inside the neuron budget and the ledger cap, and triggered screenshots for pages with mentions (E7).
- [ ] The admin shows edges, conditions and suggested tags (E8).
- [ ] Docs are synchronised and the operator checklist is complete, including the Workers AI token and the Workers Free plan check (E9).
- [ ] Edge emit, translation, per-document tags and automatic emit remain out of scope.
- [ ] Release PR from `feat/extraction` to `main` is ready.

**Last orchestration:** none yet. **Plan created:** 2026-10-26, alongside the crawlers revision for Cloudflare R2 and the free-tier guards.
