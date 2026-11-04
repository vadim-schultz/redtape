# Discovery layer operations runbook

GovData and PVOG catalogue ingest, FIM/LeiKa enrich, the queue-based crawl layer (payload harvest, Cloudflare
rendered snapshots, screenshots, document candidates), admin review, and machine emit to `pending`
suggestions. Canon URLs, ingest vs enrich roles, and staging contract pointers:
[`government-data-sources.md`](../discovery/government-data-sources.md).
Manual operator steps that unlock the live gates: [crawlers-operator-checklist.md](crawlers-operator-checklist.md).

## Emit, vote and promote are dormant

Since the [document-browse-confidence](../../.plans/document-browse-confidence/00-architecture.md) suite,
emit -> vote -> promote is **dormant**. Tag confidence replaced the accept/reject gate, so publishing a
document through it is moot: the public `/documents` list reads the staged candidates directly
([candidate-view.md](candidate-view.md)), whether or not they were emitted. Nothing in the browse flow
emits, votes or promotes a candidate.

| Piece | State |
| --- | --- |
| Machine emit routes, `candidates emit`, the admin Emit panel and the emit preview | Kept and working. They create `pending` suggestions; no schedule calls them. |
| Suggestion API, voting (`PUT`/`DELETE /api/v1/suggestions/{id}/vote`) and promotion at +3 votes | Kept and unchanged. Nobody is directed to them. |
| Web `/suggest` (submit form) and its menu link | Removed. `/suggestions` and `/suggestions/:id` remain (the admin Emit panel links to them). |
| `document` table, `GET /api/v1/documents`, `GET /api/v1/matrix`, web `/documents/:id` | Kept, but empty: the sample documents are gone and the list no longer reads them. |

Decisions D1, D3 and the open seam S5 are in
[gaps-and-decisions.md](../../.plans/document-browse-confidence/gaps-and-decisions.md). The sections below
still describe the machine routes and commands accurately; read them as maintenance procedures, not as the
publishing path.

## Production — scheduled ingest (primary)

**Operators should use GitHub Actions**, not a laptop, for recurring catalogue refetch and worker drain
against production Render.

| Topic | Doc |
| --- | --- |
| Discovery online runbook (dispatch, secrets, triage, idempotency) | [discovery-online.md](discovery-online.md) |
| Monthly OpenPLZ / discovery schedule and secrets | [scheduled-jobs.md](scheduled-jobs.md) |
| Drains (HTTP kinds, browser kinds), kind filter, retry, browser budgets | [discovery-online.md](discovery-online.md) § Bounded drain |
| Drain workflows, ledger caps, schedule variables | [scheduled-jobs.md](scheduled-jobs.md) |
| Workflow | [platform-maintenance.yml](../../.github/workflows/platform-maintenance.yml) |

Scheduled runs update **staging only** — no automatic emit to suggestions. Emit stays manual (§
Machine emit and § Manual candidate emit below).

## Laptop debugging (secondary)

The sections below describe a **local** stack for fixtures, enrich CLIs, admin smoke, and manual emit.

**Chief-of-staff orchestration** (chapter order, loop branch, release) is documented separately in
[`loops/discovery-layer.md`](loops/discovery-layer.md).

External portals and proxy notes:
[`docs/discovery/government-data-sources.md`](../discovery/government-data-sources.md).

## Prerequisites

- Local stack per [`local-development.md`](local-development.md) (Postgres, API on port 8000, web on 5173).
- Discovery staging migration applied: `cd apps/api && alembic upgrade head`.
- Germany country jurisdiction available for federal ingest — the MVP seed includes
  `11111111-1111-1111-1111-111111111101` (`python -m scripts.seed_jurisdictions` after migrations).

## Environment variables

Set these in `apps/api/.env` (API + admin) and export the same `DISCOVERY_API_*` values for
`apps/discovery-ingest` CLI runs. See also [`apps/api/.env.example`](../../apps/api/.env.example).

| Variable | Where | Purpose |
| --- | --- | --- |
| `DISCOVERY_ADMIN_EMAILS` | API | Comma-separated emails allowed to call `/api/v1/discovery/admin/*` and open `/admin/discovery/*` in the web app |
| `DISCOVERY_API_URL` | Ingest CLIs | API **host root** (no `/api/...` suffix). Local: `http://localhost:8000`. Production: `https://redtape-api.onrender.com`. `discovery-ingest` appends `/api/v1/discovery/machine/...`. |
| `DISCOVERY_API_KEY` | Ingest CLIs | Plaintext crawler key (`X-API-Key`) with access to discovery machine routes |
| `FEDERAL_JURISDICTION_ID` | Ingest CLIs (optional) | Germany country UUID for federal rows; default seed `11111111-1111-1111-1111-111111111101` |
| `DISCOVERY_MACHINE_OPT_IN` | API (optional) | When `1`, enables machine routes even if `DISCOVERY_ADMIN_EMAILS` is empty (dev only) |

### Issue a discovery machine API key

There is no HTTP endpoint for key issuance. From `apps/api`:

```bash
python -m scripts.issue_api_key --name discovery-ingest-local
```

For scheduled GitHub Actions discovery runs, issue a separate key:

```bash
python -m scripts.issue_api_key --name discovery-scheduled-gha
```

Store the printed `rt_…` in `DISCOVERY_API_KEY` (local shell or GitHub repository secret — see
[`scheduled-jobs.md`](scheduled-jobs.md)). Revocation and rotation follow
[`auth-setup.md` §7](auth-setup.md#7-issue-and-revoke-crawler-keys).

### Admin allowlist

Add operator emails to `DISCOVERY_ADMIN_EMAILS` (lowercase is normalized). Sign in to the web app with
Supabase using one of those addresses before visiting admin routes.

## Web admin route surface

The discovery admin UI is available only after the server admin probe succeeds. The server remains the
authorization boundary; the browser does not contain an email allowlist.

| Web route | Behavior |
| --- | --- |
| `/admin/discovery` | Redirects to the catalogue page. |
| `/admin/discovery/catalogue` | Shows catalogue rows with their own summary chips (total, source, pipeline stage) that filter the table, a Title column and a stage filter. |
| `/admin/discovery/coverage` | Shows the dedicated coverage summary and the budgets. |
| `/admin/discovery/tasks` | Shows the crawler task queue: kind, status and source filters; columns for attempts, retry time and result note. |
| `/admin/discovery/documents` | Lists document candidates: toolbar in the table header, every column sorts, filters appear as removable chips, a Ready quick filter (the five completeness flags), long titles clipped with a tooltip, paging. |
| `/admin/discovery/documents/<candidate-id>` | Shows one candidate: mentions, evidence artifacts, emit preview and suggestion state. |
| `/admin/discovery/pipeline/<catalogue-service-id>` | Shows pipeline stages, row details and the stored artifacts. |
| `/admin/discovery/unknown` | Shows the explicit Page not found fallback; it must not leave an empty outlet. |

Lists and tables share one contract and one set of components, and the release smoke checklist lives in
[admin-tables.md](admin-tables.md).

The staged candidates also have a **public** read-only view, outside this admin surface and without a guard:

| Web route | Behavior |
| --- | --- |
| `/documents` | Lists every staged candidate as a document card with a confidence circle (search, sort, life-area, life-situation and domain chips, paging). `/candidates` redirects here. |
| `/candidates/<candidate-id>` | Shows one candidate: tags, ingress and egress cards, the flow diagram, the screenshot and the sources. |

The public API routes, the deploy order, the screenshot cadence, the showcase candidates and the
release smoke checks are in [candidate-view.md](candidate-view.md).

The emit preview is a subview of the pipeline page, not a top-level route. Every discovery page has
visible loading, success, empty, and error feedback. A `401` sends the session to login, a `403` shows
the forbidden view, a `503` explains that discovery is disabled, and network/API failures offer the
existing retry action.

If the probe fails with `503`, a 5xx status, or a network error, the app retries it twice. If it still
fails, the menu shows a muted **Discovery unavailable** hint instead of the links. A `401` or `403`
shows no hint, because that case looks the same as a non-admin session.

Under **Documents**, an allowlisted user sees icon controls for **Catalogue** (`FaList`), **Coverage**
(`FaTasks`), **Tasks** (`FaClipboard`) and **Documents** (`FaFileAlt`) after the admin probe returns `200`. All of
them sit in one row; a new link is a config entry rendered through `MenuIconLink`, never a second row. Each control keeps a
translated `aria-label` and a title, and the routes are unchanged. Non-admin and anonymous sessions do not see those links,
and direct navigation remains guarded. The menu also keeps these application links:

| Menu action | Route and behavior |
| --- | --- |
| **Home** | Full-width link to `/`. |
| **Browse Documents** | Icon-only, labelled link to `/documents`. |

## Staging vocabulary and the T4 handoff

Four kinds of state exist. Do not mix them up.

| State | Where it lives | Meaning |
| --- | --- | --- |
| Catalogue state | `catalogue_service`, keyed by `(source, external_id)` | Current imported row. It is not a canonical document. |
| Task history | `discovery_task` and `discovery_fetch_log` | Durable queue work (pending, claimed, completed, failed) and append-only fetch attempts. |
| Claims | `discovery_entity` and `discovery_claim` | Staged assertions that can become suggestions. |
| Canonical documents | the document tables | Dormant: reached only through vote and promotion, which the browse flow no longer uses. |

The admin pipeline derives a stage for each catalogue row:

| Stage | Meaning |
| --- | --- |
| T0 | Row imported, no portal task. |
| T1 | Row has a portal task. |
| T2 | At least one fetch attempt is logged. |
| T3 | Entities and claims exist. |
| T4 | Claims are eligible for emit. |

T4 is an emit-readiness milestone, not a canonical-document state. The handoff stops at a pending
suggestion:

```text
T4 -> inspect emit preview -> manual machine emit -> pending suggestion
```

This process does not vote, promote, attach evidence to suggestions, or emit automatically. Snapshots and
screenshots stay staging artifacts (§ Artifacts and evidence).

### Representative smoke status

The chapter 1 smoke of the discovery-operations suite is **partial**. It covered T0, T1, and T2 plus
fixture-backed downstream contract tests. It did **not** verify a persisted T4 row or a manual emit
against a running API: the fixture row has no `fim_id`, and no authorized API session was available.
Treat the full row-to-pending-suggestion path as unverified until an operator runs it with a row
that has a `fim_id`. Evidence and gaps:
[`.plans/discovery-operations/chapters/01-representative-row-smoke.md`](../../.plans/discovery-operations/chapters/01-representative-row-smoke.md).

## Task kinds and the crawl flow

`discovery_task.kind` selects the worker handler. The worker sends a **kind filter** (`kinds`) with each claim.
Without one the API serves only the two legacy kinds, `fetch_url` and `enrich_metadata`.

| Kind | Input | Output |
| --- | --- | --- |
| `fetch_url` | catalogue `portal_url` | fetch log; a follow-up `render_page` for a 200 HTML page that is not a login URL |
| `enrich_metadata` | FIM steckbrief URL | entity and claims |
| `harvest_payload` | PVOG `raw_payload` (no network) | document mentions |
| `extract_page` | stored HTML snapshot (no network) | document mentions |
| `render_page` | page URL, Cloudflare Browser Run | `html_snapshot` artifact |
| `capture_screenshot` | page URL, Cloudflare Browser Run | `screenshot` artifact |
| `llm_extract` | stored HTML snapshot, Cloudflare Workers AI (budgeted: neurons, never in the default kinds) | document mentions with conditions and tag codes, staged edges |

```text
catalogue row -> fetch_url -> render_page -> snapshot -> extract_page -> mentions -> candidates
catalogue row -> harvest_payload ----------------------------------> mentions -> candidates
extract_page (at least one mention) -> capture_screenshot -> screenshot
snapshot -> llm_extract -> mentions, staged edges, tag codes -> candidates (at least one mention: capture_screenshot)
candidates -> admin review -> manual emit -> pending new_document suggestion
```

Only `llm_extract` queues a capture, and only after it posts mentions. A page that was extracted earlier has none.
`capture requeue` queues `capture_screenshot` for each page that carries candidate mentions and has no screenshot (it
reads them from `GET /machine/candidates/sources`). Its identity is the catalogue row, the kind, the URL and `shot@1`, so
a repeated run reports `already_queued` and never duplicates. Then drain `capture_screenshot` on a laptop
([discovery-online.md](discovery-online.md) § Run a browser drain on a laptop).

The default drain handles `fetch_url`, `enrich_metadata`, `harvest_payload` and `extract_page`. The browser kinds are
drained only by `discovery-render.yml` or an explicit `--kinds`, with a browser budget. Flags, retry rules, stop
reasons and limits: [discovery-online.md](discovery-online.md) § Bounded drain and § Browser kinds.

## Document candidates and mentions

The crawl layer is **document-first**: it builds document nodes before any edge between documents.

| Term | Meaning |
| --- | --- |
| Procedure | A catalogue service (a Leistung, for example "Anmeldung einer Wohnung"). Staging context, never a document node |
| Candidate | A deduplicated document name harvested from one or more sources, not yet emitted. Status `staged`, then `emitted` |
| Mention | One occurrence of a candidate in a procedure: role (`required`, `form` or `issued`), excerpt, source field, extractor and version, optional artifact; extracted mentions also carry a condition, an optional flag and the page's domain and life-situation codes |
| Edge | A staged `parent requires required` link between two candidates, with the procedure as provenance, a condition and an optional flag. Staged only (see below) |
| Key | `slugify(pick_title(title_i18n))`, the same rule promotion uses, so two candidates never collide at promotion without colliding as candidates |

**A procedure is not a document.** Service-level `new_document` claims that FIM enrichment writes for a procedure's
own title stay staged and are excluded from the document-first path. Only what a procedure requires or provides
(forms, documents to bring) becomes a candidate.

Sources today: `harvest_payload` reads PVOG modules `08` (required documents) and `14` (forms) from the stored
payload, and `llm_extract` reads the free text of a stored snapshot (next section). Hand-written page extractors are a
framework (`discovery_ingest/extract`); none is registered yet.

## Extracted documents, edges and tags (`llm_extract`)

`llm_extract` is the general reader for pages that carry no structured payload. It runs one model call per stored
snapshot and stages the result; it emits nothing. Architecture, decisions and the chapter ledger:
[`.plans/extraction/`](../../.plans/extraction/00-architecture.md). Drain commands and flags:
[`apps/discovery-ingest/README.md`](../../apps/discovery-ingest/README.md) and
[discovery-online.md](discovery-online.md) § LLM kind. Operator steps: [extraction-operator-checklist.md](extraction-operator-checklist.md).

- **Budgeted kind.** `llm_extract` spends Cloudflare Workers AI neurons (10,000 a day on the Workers Free plan, 9,500
  under the ledger cap). It is never in the default kinds, is drained only with an explicit `--kinds llm_extract` and a
  `--neuron-budget`, and every call reserves neurons from the budget ledger first. A limit releases tasks; it never
  fails a page.
- **Grounding rule.** The page is cleaned first (`CLEAN_VERSION`, at most 30,000 characters). The model answers in JSON
  mode with a name, a role and a verbatim quote for each document. An item whose quote, after the shared
  normalisation (case, whitespace, list bullets, quote marks, dashes, markdown markers and link targets folded on both
  sides), is not on the page is dropped. A URL that is not a link of the page is cleared. A code outside the taxonomy is
  dropped. Names that are data fields (an address, a number) or generic words (a leaflet, a device) are dropped too.
  Percent-encoded text the model sometimes returns is decoded before the check.
- **Role `issued`.** The document a procedure results in. When a page has exactly one `issued` document, every
  `required` document of the page gets a `derived_single_issued` edge from it; the model's own `dependencies` become
  `explicit` edges. Edges live in `discovery_candidate_edge` and are read at
  `GET /admin/candidates/{id}/edges`. **Edges are staged, not emitted**: no route or schedule turns them into
  requirements, and candidate emit (above) still carries documents only.
- **Conditions.** A mention keeps the page's condition ("bei Zuzug aus dem Ausland") and an optional flag. Names stay
  German and verbatim; no translation is made.
- **Taxonomy route.** `GET /machine/taxonomy` returns the closed vocabulary (13 domains, 18 life situations, with
  German and English names) that the worker puts in the prompt. The model tags the page, not each document; the page's
  codes are copied onto its mentions.
- **Tag confidence score.** Every code of a candidate has a combined confidence score — the noisy-OR of its
  LLM-evidence curve and any direct-source confidence (a PVOG leaf, a curator's manual override). The public
  list and its chip filters use **every** score, with no floor: the score only orders and colours
  ([candidate-view.md](candidate-view.md)). The floor `MIN_SUGGESTED_SCORE` (0.05), a noise floor and not a
  precision claim, applies now only to the emit payload (the codes a `new_document` suggestion carries) and to the
  completeness flags `has_domain` and `has_situation`. The admin candidate detail shows each code with its support
  (`procedures`, `share`, `score`); nothing is written to a document automatically.
- **Re-extraction is deliberate.** The task key is `llm:` plus eight hex digits of the model, `PROMPT_VERSION`
  (`ext-6`) and `CLEAN_VERSION` (`clean-4`). The identity of a task is the catalogue row, the kind, the target URL and
  that key, so a re-render under the same versions queues no second task; only `llm requeue` after a model, prompt or
  cleaner change queues one. LLM mentions use a fixed `source_field`, so a re-run updates them in place.

## Manual candidate emit

Emit turns reviewed candidates into **pending** `new_document` suggestions. It is a deliberate operator action: no
schedule calls it. It is **dormant** in the browse flow: a candidate is listed on `/documents` without it.

```bash
python -m discovery_ingest candidates emit --all-staged --min-mentions 3 --limit 5 --dry-run
python -m discovery_ingest candidates emit --all-staged --min-mentions 3 --limit 5
python -m discovery_ingest candidates emit --id <candidate-uuid> --id <candidate-uuid>
```

| Flag | Default | Meaning |
| --- | --- | --- |
| `--id` | none | Candidate to emit; repeatable. Mutually exclusive with `--all-staged` |
| `--all-staged` | off | The most mentioned staged candidates |
| `--min-mentions` | 0 | With `--all-staged`: minimum mention count |
| `--limit` | 10 | Maximum candidates, 1–50 |
| `--dry-run` | off | Preview only; nothing is written |

The command prints `created <candidate> <suggestion>`, `replayed …` or `skipped <candidate> <reason>`. Skip reasons:
`not_found`, `no_mentions`, `no_source_url`, `invalid_payload`, `duplicate`, `already_emitted` (preview only). The
suggestion's `source_url` is the `portal_url` of the first mention's procedure. Emit is idempotent per candidate and
records the suggestion on the candidate. `official_url` is optional on `new_document`, so a candidate without a URL
conflicts on its slug only ([suggestion-api.md](suggestion-api.md)). Review five, then widen; never bulk-emit before the
first five are checked.

## Artifacts and evidence

Snapshots and screenshots are stored in an S3-compatible object store (Cloudflare R2 in production); Postgres holds only
metadata rows in `discovery_artifact`. The API proxies uploads and mints five-minute presigned URLs for reads, so
storage credentials live only in Render ([deployment-checklist.md](deployment-checklist.md)). HTML is never rendered
inline in the admin: it is a download. The screenshot is the visual.

Each artifacts refetch in the admin costs one R2 Class B read per link, up to 50 links. The admin pages cache for four
minutes.

## Machine and admin routes added by the crawl layer

All machine routes take `X-API-Key` and live under `/api/v1/discovery/machine`. Admin routes take a session token for
an allowlisted email and live under `/api/v1/discovery/admin`.

| Route | Purpose |
| --- | --- |
| `GET /machine/tasks/summary` (repeated `kinds`) | Queue counts for the drained kinds: `pending_ready`, `pending_delayed`, `claimed`, `claimed_stale`, `completed`, `failed` |
| `POST /machine/tasks` | Enqueue a follow-up task (`kind`, `target_url`, `priority`, `input_key`, `artifact_id`) |
| `POST /machine/tasks/{id}/release` | Return a claimed task to `pending`, give the attempt back; 409 if not claimed |
| `POST /machine/tasks/{id}/fail` | Fail with `retryable`; a retryable failure re-pends with backoff |
| `POST /machine/tasks/{id}/complete` | Complete, with an optional result `note` |
| `POST /machine/tasks/{id}/artifacts` | Upload a snapshot or screenshot (multipart): 415, 413, 503, 507 |
| `GET /machine/artifacts`, `…/{id}/content`, `…/status` | List (`kind`, `host`), read bytes, and check `storage_enabled` and the byte accounting |
| `GET /machine/candidates/sources` | Catalogue rows with at least one candidate mention and the newest `html_snapshot` url of each (`missing=screenshot`, `host`, `candidate_id`, repeated `catalogue_service_id` up to 20, `offset`, `limit`); read-only; the input of `capture requeue`; see [candidate-view.md](candidate-view.md#screenshot-cadence) |
| `POST /machine/candidates/mentions` | Post mentions for a candidate (role, condition, optional flag, tag codes; the response counts `unknown_codes`) |
| `POST /machine/candidates/edges` | Post staged edges: answers `{edges_created, edges_updated, edges_skipped, skipped}` |
| `GET /machine/taxonomy` | The closed vocabulary of domain and life-situation codes the prompt uses |
| `GET /machine/candidates`, `GET …/{id}/emit-preview`, `POST /machine/candidates/emit` | Select, preview and emit candidates (50 per call) |
| `GET /machine/budgets`, `POST …/budgets/{resource}/{reserve,adjust,exhaust}` | The budget ledger; a denied reserve answers 409 |
| `GET /admin/candidates`, `GET …/{id}`, `GET …/{id}/emit-preview` | Candidate list (canonical `q`, `sort_by` including `completeness`, `sort_order`, `filter[status\|role\|source\|min_mentions\|jurisdiction\|domain\|situation]` and the yes/no completeness flags `filter[has_domain\|has_situation\|has_edges\|has_snapshot\|has_screenshot\|complete]`; legacy `status`, `role`, `source`, `min_mentions`, `sort` still accepted and overridden by the canonical form; unknown fields or invalid values answer 422 listing each bad parameter), detail and preview |
| `GET /admin/tasks` | Crawler queue (canonical `q` over the target URL, `sort_by` `target\|kind\|status\|source\|priority\|attempts` with `sort_order`, `filter[status\|source\|kind]`; legacy `status`, `source`, `kind` still accepted and overridden by the canonical form; ties fall back to the queue order; invalid values answer 422) |
| `GET /admin/catalogue` | Imported catalogue (canonical `q` over the external id, `sort_by` `external_id\|title\|source\|stage` with `sort_order`, `filter[source\|stage]`; legacy `source` still accepted; newest first by default; paged with `offset` and `limit`; `total` and the summary follow the filter) |
| `GET /admin/candidates/{id}/edges` | Staged edges of a candidate, both directions, with basis, condition and the procedure |
| `GET /admin/catalogue/{id}/artifacts`, `GET /admin/candidates/{id}/artifacts` | Artifacts with presigned `url` (`null` when storage is unset) |
| `GET /admin/budgets` | The ledger plus `stored_bytes` and `stored_bytes_cap` |

The admin task list accepts `kind`, `status` and `source`; an invalid value answers 422.

## Corporate network (ingest only)

GovData CKAN, PVOG, and FIM/LeiKa calls from your laptop usually need the corporate HTTP proxy.
The local Redtape API stays direct via `NO_PROXY`.

Export before live ingest or `curl` checks (values from
[corporate-build-env.md](../../.cursor/skills/chief-of-staff/corporate-build-env.md)):

```bash
export HTTP_PROXY=http://185.46.212.88:9480/
export HTTPS_PROXY=http://185.46.212.88:9480/
export NO_PROXY=localhost,127.0.0.1,.rsint.net,.rsext.net
```

CI and unit tests use fixtures only — they do not call GovData, FITKO, or `fimportal.de`.

## Manual sequence (local)

Run steps in order for a full local pass. Fixture paths and field names:
[`government-data-sources.md`](../discovery/government-data-sources.md).

### 1. Migrate and seed

```bash
docker compose up -d --wait db
cd apps/api
source .venv/bin/activate
alembic upgrade head
python -m scripts.seed_jurisdictions   # if jurisdictions are not already present
```

### 2. GovData OZG ingest (fixture or export file)

From `apps/discovery-ingest` with venv and deps installed (`uv pip install -e ".[dev]"`):

```bash
export DISCOVERY_API_URL=http://localhost:8000
export DISCOVERY_API_KEY=rt_<your-key>

python -m discovery_ingest govdata run \
  --input path/to/ozg-leistungen-page.json \
  --jurisdiction-id 11111111-1111-1111-1111-111111111101
```

Live CKAN export: see canon § GovData; verify connectivity with proxy env set.

### 3. PVOG Suchdienst ingest

```bash
python -m discovery_ingest pvog run \
  --jurisdiction-id 11111111-1111-1111-1111-111111111101
```

Uses `PVOG_API_BASE_URL` when overridden; default host is in
[`discovery_ingest/config.py`](../../apps/discovery-ingest/discovery_ingest/config.py).

### 4. FIM / LeiKa enrich

Save an admin catalogue JSON snapshot (array of rows from
`GET /api/v1/discovery/admin/catalogue`, or a test fixture under
`apps/discovery-ingest/tests/fixtures/`). Then:

```bash
python -m discovery_ingest fim enrich \
  --catalogue-service-id <uuid> \
  --catalogue-export path/to/catalogue_export.json \
  --input path/to/steckbrief.json

python -m discovery_ingest leika enrich \
  --catalogue-service-id <uuid> \
  --catalogue-export path/to/catalogue_export.json \
  --input path/to/stammtext.json
```

To check live keys without saving a snapshot, probe the public FIM portal through the hardened fetcher:

```bash
python -m discovery_ingest fim probe --keys 99154021000000,99070016261000
```

It prints each status and the top-level keys, and exits 1 when the decision gate fails (a key did not return
`leistungsschluessel`). The manual workflow is [`discovery-fim-probe.yml`](../../.github/workflows/discovery-fim-probe.yml).

**Steckbrief key.** Fanout enqueues `enrich_metadata` for GovData and PVOG rows. The key is the first 14-digit value of
`fim_id`, `leistungsschluessel`, `leika_key`, `leikakeys[0]`. The probe of ten live keys passed on 2026-10-26.

**Label and claims.** The real steckbrief has top-level `title`, `title_en`, `leistungsbezeichnung`,
`leistungsschluessel`, `rechtsgrundlagen`, `klassifizierung`, `leistung_stammtexte` and others, but no `titel`, no
`kurztext` and no document or form field. The entity label is the first non-blank of `title`, `titel` (the legacy
shape of the early fixtures) and `leistungsbezeichnung`; with none of them the entity is still created without a label.
The `metadata` claim (`kurztext`) is written only when a response carries a real `kurztext`, which the steckbrief does
not, so enriched entities get a label and the staged service-level `new_document` claim, and no `metadata` claim. No
other field stands in for `kurztext`, and the `new_document` title still comes from the catalogue row. Stammtext
references (`leistung_stammtexte`) are not fetched.

### 5. Admin review (smoke)

Unit tests are not a live smoke. They show that the route tree and the guard outcomes work in a test
renderer; they do not show that the deployed API, auth configuration, and web proxy work. Run the
sequence below against the target environment and record each result.

1. **Worker-origin check.** Send `GET /api/v1/discovery/admin/tasks?limit=1` with a valid bearer token
   to the web origin. Expect `200` for an allowlisted user. Compare with the direct API origin if the
   status differs (see section 7). Do not paste or commit the token.
2. **Sign-in check.** Sign in with an email that is on `DISCOVERY_ADMIN_EMAILS`. Open the menu and
   confirm that **Catalogue**, **Coverage**, **Tasks** and **Documents** appear under **Documents** in one row. A muted
   **Discovery unavailable** hint means the probe failed with 503, 5xx, or a network error.
3. **Page checks.** Open each page and confirm content or a deliberate loading, empty, or error state.
   The browser console must show no `No routes matched location` warning.

| Surface | URL / route |
| --- | --- |
| Discovery admin root | Web: [`/admin/discovery`](http://localhost:5173/admin/discovery), redirects to the catalogue |
| Crawler queue | Web: [`/admin/discovery/tasks`](http://localhost:5173/admin/discovery/tasks) |
| Catalogue index and coverage chips | [`/admin/discovery/catalogue`](http://localhost:5173/admin/discovery/catalogue) |
| Dedicated coverage summary | [`/admin/discovery/coverage`](http://localhost:5173/admin/discovery/coverage) |
| Document candidates | `/admin/discovery/documents` |
| Document detail and evidence | `/admin/discovery/documents/<candidate-id>` |
| Pipeline + emit preview + artifacts | `/admin/discovery/pipeline/<catalogue-service-id>` |

Also confirm that an unknown discovery route shows **Page not found**, that a non-allowlisted user sees
no discovery links and the forbidden view on direct navigation, and that Home and Browse Documents
keep their menu routes (there is no Suggest link). Locally, use `./scripts/dev-up.sh` or a manual API and web start.

Admin JSON API (session JWT, allowlisted email): prefix
`http://localhost:8000/api/v1/discovery/admin` — e.g. `GET …/catalogue`, `GET …/coverage`.

### 6. Machine emit to suggestions

This section emits **catalogue claims**. To emit reviewed **document candidates**, see § Manual candidate emit.

Emit is a machine API operation. It creates **`pending`** suggestions only (no voting or promotion):

```text
POST /api/v1/discovery/machine/catalogue/<catalogue-service-id>/emit
```

```bash
curl -s -X POST \
  "http://localhost:8000/api/v1/discovery/machine/catalogue/<catalogue-service-id>/emit" \
  -H "X-API-Key: rt_<your-key>" | python -m json.tool
```

The admin emit preview (`GET …/emit-preview`, shown on the pipeline page) is read-only and does not
emit. Use it first; mapping code is in
[`emit_preview.py`](../../apps/api/app/features/discovery/emit_preview.py).

| Claim kind | Emit behavior |
| --- | --- |
| `new_document` | Eligible only when the title and official URL fields are present. |
| `metadata` | Preview-only (`metadata_not_emitted`); not emitted. |
| `new_requirement` | Skipped (`unresolved_requirement_documents`) until both document UUIDs resolve. |

Emit is idempotent by claim identity. A replay returns the existing suggestion and creates no
duplicate. The suggestion stays `pending` until a vote or a moderator acts on it, which the browse flow no longer
needs (dormant).

**Emit one verified row first.** Open its pipeline page, confirm T4 and the preview, emit that single
row, and check the response counts (`created_count`, `skipped_count`, `replayed_count`) and the
suggestion ID. Do not bulk emit until that smoke is clean. Verify in the admin preview or
`GET /api/v1/suggestions` (public list).

### 7. Admin probe triage (blank admin page or missing menu links)

A blank admin page body with the shell visible, and the browser console warning
`No routes matched location "/admin/discovery/..."`, means a route-nesting defect (fixed by relative
child paths under the `/admin/discovery/*` mount). Missing menu links mean the probe below did not
return `200`.

The menu shows the discovery admin links only when
`GET /api/v1/discovery/admin/tasks?limit=1` succeeds for the signed-in user. Read the HTTP status
of that request (browser devtools, then curl against the web origin and
`https://redtape-api.onrender.com`; never paste or commit tokens) and use this table.

| Probe status | Cause | Fix |
| --- | --- | --- |
| 200 | Probe works | Inspect the deployed bundle and menu code |
| 401 | No or invalid bearer token, or `auth_enabled` is false. A curl request without a token always returns 401 | Send a fresh bearer token; if a valid token still gets 401, check both Supabase variables on Render |
| 403 | Email not on `DISCOVERY_ADMIN_EMAILS` (compared lowercase) | Add the exact login email on Render |
| 503 | Discovery disabled, or cold start / proxy 503 (menu shows **Discovery unavailable** after two retries) | Enable discovery; repeat after `/health` is warm |
| 500 | Authenticated, but the guard or handler crashed. `/api/v1/me` 200 with `/discovery/admin/*` 500 is a code fault, not config: read the traceback in Render logs (e.g. `DetachedInstanceError`) | Check Render logs; see "Logging gap" below |
| 5xx / timeout | Cold start or API fault (menu shows **Discovery unavailable** after two retries) | Check Render logs |

Triage record (operator-reported, 2026-10):

- Probe returned **401** `{"status_code":401,"detail":"Not authenticated"}` while signed in. Whether
  this was browser or curl, and which origin, is **unconfirmed**.
- Render: `DISCOVERY_ADMIN_EMAILS` holds the operator email, so 403 is ruled out;
  `DISCOVERY_MACHINE_OPT_IN` is false (irrelevant to admin routes). Auth-enabled state was not reported.
- Admin pages render blank in the browser, consistent with the route-nesting defect; whether the
  `No routes matched location` console warning appears was not reported.
- Cloudflare serves deployment `59339dfc-06e3-4470-bbf8-0cd27e6e8dce` (not yet verified against `main`).

Correction (2026-10-22): the earlier theory that Supabase variables were unset on Render was wrong. The
401 came from a request that carried no bearer token. Verified facts:

- `/api/v1/me` returned 200, so JWT auth and the Supabase variables work.
- `/discovery/admin/tasks`, `/coverage` and `/catalogue` returned 500 every time.
- Alembic was at head (`20261015_claim_fingerprint`), all six discovery tables, the
  `payload_fingerprint` column and five enum types existed, and 1413 catalogue rows were present.
- Root cause: `require_discovery_admin_allowlist` read `user.email` after its session closed
  (`DetachedInstanceError`). Fixed by reading the email inside the session block.

### Verifying the schema

Run these in the Supabase SQL editor when triaging a 5xx:

```sql
select version_num from alembic_version;
select table_name from information_schema.tables
  where table_schema = 'public' and (table_name like '%discovery%' or table_name like 'catalogue%');
select column_name from information_schema.columns where column_name = 'payload_fingerprint';
select typname from pg_type where typtype = 'e' order by typname;
```

### Logging gap

Render logs showed only access lines for the 500s, with no traceback. The Litestar app in
`apps/api/app/main.py` sets no `logging_config`, and Litestar logs unhandled exceptions only in debug
mode by default. Until that is changed (follow-up), reproduce locally to see the traceback.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Admin page blank, console warns `No routes matched location` | Section 7; confirm the deployed build includes the relative-route fix |
| Discovery links missing but `/me` is 200 | Check the probe status (section 7); on 500 read the Render logs traceback |
| Admin UI forbidden | `DISCOVERY_ADMIN_EMAILS` includes your signed-in email; discovery feature enabled |
| Machine routes 401 | Valid `DISCOVERY_API_KEY`; or `DISCOVERY_MACHINE_OPT_IN=1` for local dev |
| Ingest TLS timeout / reset | Corporate `HTTP_PROXY` / `HTTPS_PROXY`; `NO_PROXY` includes `localhost` |
| GovData/PVOG CLI exits 1 | API logs; machine batch errors; jurisdiction UUID exists |
| Drain of a browser kind exits 2 | `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_BROWSER_API_TOKEN` are exported ([discovery-online.md](discovery-online.md) § Browser kinds) |
| Drain of a browser kind exits 1 before claiming | `GET …/machine/artifacts/status` shows `storage_enabled: false`; set the Render `OBJECT_STORE_*` variables |
| Artifact routes answer 503 or 507 | 503: storage unset or an operation cap reached; 507: the byte cap ([deployment-checklist.md](deployment-checklist.md)) |
| Machine writes answer 507 `database_soft_limit` | Database above 475 MB; free space or raise `DB_SOFT_LIMIT_BYTES` knowingly |
| Admin tasks filter answers 422 | `kind`, `status` or `source` is not a known value |

Scheduled GitHub Actions ingest uses the same host-root `DISCOVERY_API_URL` and repository secrets
documented in [`scheduled-jobs.md`](scheduled-jobs.md).
