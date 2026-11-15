# Translation engines: Azure AI Translator, the character ledger and rollback

This runbook covers the translation pipeline on `azure-translator`, the default engine. Three things use it: the
card drain (`translate drain`, title and description of each candidate), the snapshot drain (`translate drain --unit
snapshot`, the text of each procedure page) and the interface strings (`i18n translate-ui`). The figures below are for
the default configuration.

Related: [scheduled-jobs.md](scheduled-jobs.md) (the workflows and their schedules), [gha-budget.md](gha-budget.md)
(Actions minutes), [deployment-checklist.md](deployment-checklist.md) (the cap table), [locales.md](locales.md)
(enabling interface locales), [discovery-translate.yml](../../.github/workflows/discovery-translate.yml).

## Engines

`TRANSLATION_ENGINE` selects the engine for the card drain and for `translate-ui`. Unset means `azure-translator`. The
name must be a registered engine. An unknown name fails at load: the CLI exits 2 and lists the registered names.

| `TRANSLATION_ENGINE` | Provider | Usage unit | Ledger | Use |
| --- | --- | --- | --- | --- |
| `azure-translator` (default) | Azure AI Translator, NMT, API version `2026-06-06` | characters | `azure_translator_chars`, monthly (UTC) | Cards and interface strings |
| `llm` | Cloudflare Workers AI, `@cf/qwen/qwen3-30b-a3b-fp8` | neurons | `neurons`, daily, shared with extraction and embedding | Rollback |

The snapshot drain always uses `azure-translator`, whatever `TRANSLATION_ENGINE` says. `claude-code` is also registered
in the code. This runbook does not cover it.

## Secrets and variables

Secrets are GitHub Actions secrets. The translate jobs run in the `discovery-translate` environment and read them there.
Never commit a value. The workflow checks that a required secret is set and names it when it is not, but never prints
its value.

| Secret | Used by | Notes |
| --- | --- | --- |
| `DISCOVERY_API_URL` | every translate job | API host root, without a path |
| `DISCOVERY_API_KEY` | every translate job | The machine key |
| `AZURE_TRANSLATOR_KEY` | `azure-translator` and the snapshot job | Required |
| `AZURE_TRANSLATOR_REGION` | `azure-translator` and the snapshot job | Required: the region of the Translator resource |
| `AZURE_TRANSLATOR_ENDPOINT` | `azure-translator` and the snapshot job | Optional. Unset means the global host `https://api.cognitive.microsofttranslator.com` |
| `CLOUDFLARE_ACCOUNT_ID` | `llm` only | |
| `CLOUDFLARE_AI_API_TOKEN` | `llm` only | A token with only the Workers AI permission |

GitHub variables (Settings, Secrets and variables, Actions, Variables):

| Variable | Default | Purpose |
| --- | --- | --- |
| `TRANSLATION_ENGINE` | `azure-translator` | The card drain and `translate-ui` engine. Set `llm` to roll back |
| `TRANSLATION_GLOSSARY_MODE` | `strict` | `strict` or `advisory`. Set it from the probe's `recommended_glossary_mode` (see Probe) |
| `AZURE_TRANSLATOR_MIN_REMAINING_CHARS` | `20000` | The `azure-translator` precheck: the job skips when fewer characters remain this month |
| `AZURE_DOCUMENT_BUDGET_SHARE` | `0.6` | The ceiling of the share of the monthly cap that snapshot pages may use. The drain takes less when cards have more pending work (see The character ledger below) |
| `AZURE_WINDOW_ANCHOR` | `2026-11-13` | The first day (UTC) of the Azure allowance window. The daily pace counts the days left to the next anniversary of this day |
| `AZURE_DAILY_CHAR_PACE` | unset | Characters a run may spend today. Unset, the drain computes the day's share of what the window has left |
| `QUERY_EMBED_RESERVE` | `1000` | `llm` only: neurons the drain leaves for query embedding |
| `DISCOVERY_TRANSLATE_SCHEDULE` | unset | `enabled` turns on the daily card drain. Manual dispatch works either way |
| `SNAPSHOT_TRANSLATE_SCHEDULE` | unset | `enabled` turns on the snapshot job. Set it after the first inspected drain (see Snapshot schedule) |

API variables on Render (`redtape-api`, set in the dashboard, never in `render.yaml`):

| Variable | Default | Purpose |
| --- | --- | --- |
| `TRANSLATION_TARGET_LOCALES` | `en tr ru uk pl ro` | The target locales of cards and snapshots: the embedding set minus `de`. A test holds it equal to the worker default. Empty switches translation off |
| `TRANSLATION_UNIT_RECIPE_VERSION` | `v1` | Bump it only when the card unit is built differently: every card translation then turns stale |
| `BUDGET_AZURE_TRANSLATOR_CHARS_MONTHLY` | `1900000` | The monthly cap of the ledger. Set it only to tighten the cap |

The worker reads the same names from `apps/discovery-ingest/.env` locally (see `.env.example`). The Azure key, region,
endpoint and API version (`AZURE_TRANSLATOR_API_VERSION`, default `2026-06-06`) are read there too, and the request shape
is written for that version only: the v3.0 API is not compatible. `TRANSLATION_MODEL` overrides the model of `llm` only.
`CLAUDE_TRANSLATE_MODEL` is read only by the `claude-code` engine, which this runbook does not cover.

## The character ledger, the cap and the document share

- The ledger resource `azure_translator_chars` counts characters for each UTC calendar month (`%Y-%m`). The API keeps
  it, so GitHub runs, laptop runs and `translate-ui` share one count. The daily pace reads the remainder of that row, but
  counts its days to the end of the anchored window (`AZURE_WINDOW_ANCHOR`). Until the API's period is anchored too, the
  row resets on the calendar month, so the two agree only while the window and the calendar month start together. `python -m discovery_ingest budget show --resource
  azure_translator_chars` prints it.
- The cap is 1,900,000 characters: 95 percent of the free F0 allowance of 2,000,000 a month, the repository's margin for
  free tiers. F0 also has an hourly sliding-window quota of the same size. At this volume the hourly quota does not bind.
- Each call reserves its exact characters before it is sent, all or nothing. A refused reservation stops the drain and
  releases its tasks without consuming an attempt. After the call, the ledger is settled to the characters Azure reports
  in the `X-metered-usage` header. Each target locale counts separately: a 3,000-character text sent to three targets
  is 9,000 characters.
- Documents share the cap with cards and interface strings. The snapshot drain's share follows the pending documents
  and cards, and never exceeds `AZURE_DOCUMENT_BUDGET_SHARE` (default 0.6). Cards therefore keep at least 40% of the cap.
  A run also stops at today's pace: the remainder over the days left in the anchored window, unless
  `AZURE_DAILY_CHAR_PACE` sets it.
- Azure answers `403001` when the free quota is used up. That stops the drain and marks the month exhausted in the
  ledger. Throttling (HTTP 429, codes 429000 to 429002) is a rate limit: the request waits (its `Retry-After` when Azure
  sends one, otherwise 2 s, then 4 s) and is sent again, at most twice. If it is still throttled, the batch's tasks are
  released without an attempt and the drain stops `rate_limited`. Azure documents no `Retry-After` header.
- The adapter sends at most 500 inputs and 28,000 characters in one request, and holds the characters it sends in any 60
  seconds at or below 28,000. The free tier enforces 33,300 a minute; the headroom covers requests in flight. Calls are at
  least one second apart. A single text over 28,000 characters is refused before anything is sent. Text is sent as
  `plain`: the snapshot unit goes as a list of blocks, not as markup.
- The `neuron_budget` option of the drain does not apply to `azure-translator`. Its characters are bounded by the
  monthly ledger and by the precheck, not by neurons.

Cost figures, copied once from the architecture. The rows assume five target locales:

| Quantity | Value | Basis |
| --- | --- | --- |
| Monthly cap | 1,900,000 characters | `BUDGET_AZURE_TRANSLATOR_CHARS_MONTHLY` |
| Card and interface-string band | about 760,000 characters | 40% of the cap |
| Document share | about 1,140,000 characters | 60% of the cap |
| Median cleaned page | about 4,300 characters | gold fixtures README, 20 pages |
| One page in 5 target locales | about 21,500 characters | median × 5 |
| Pages per month in the document share | about 50 | 1,140,000 ÷ 21,500 |
| Worst-case page at the 30,000 cap | 150,000 characters across 5 locales | about 13% of the share |
| One candidate card in 5 locales | about 2,000 characters | title plus description (cut at 300) × 5 |
| Candidates per month in the card band | about 380 | 760,000 ÷ 2,000 |
| Candidates per month if documents are paused | about 950 | 1,900,000 ÷ 2,000 |

The target list has six locales, `en` included. For six locales, the same arithmetic gives about 25,800 characters a
page (about 44 pages a month in the document share), about 2,400 characters a card (about 317 cards a month in the card
band, about 790 if documents are paused). The first month clears only part of the card and interface-string backlog.
The backlog drains over months, best confidence first. The levers are narrower target locales or moving to S1. S1 is a
configuration change: raise the cap, and the F0 limit in this runbook no longer applies.

## Probe (operator, manual, never in CI)

The probe is the live check of the engine on reviewed text. Until its report is recorded in the run ledger,
`TRANSLATION_GLOSSARY_MODE` stays at `strict`.

1. Record the data-processing and region decision (see Data processing and region) in the run ledger first.
2. Export the key in the shell only. Do not put it in a file that Git can see.
3. Keep the reviewed sample of about 20 German card units outside the repository, and pass it with `--units`. The
   repository holds no copy, and the command refuses to run without a file.
4. From `apps/discovery-ingest`:

   ```bash
   .venv/bin/python -m discovery_ingest translate probe --engine azure-translator --units <sample.json> --report <report.json>
   ```

   The probe translates every target locale through the production adapter. It spends at most `--max-usage` characters
   (default 10,000) and stores nothing.
5. Read the report. For each locale it gives the share of valid units, glossary findings, placeholder and token survival,
   and the billed and estimated characters. It also says whether HTML tags are billed, what the throttle answers were, and
   `recommended_glossary_mode`, which is `strict` only when every locale reaches 90% valid units.
6. Record the report and the glossary mode in the run ledger. Then set `TRANSLATION_GLOSSARY_MODE` to match.

`TRANSLATION_GLOSSARY_MODE` decides whether a glossary miss on a card fails the card (`strict`) or is logged while the card
is posted (`advisory`). Interface strings stay strict. Documents follow the cards' setting for now.

## Backfill order: cards, then snapshots

Run the card backfill first, then the snapshot backfill. Each queues only the tasks that are missing or stale, so a
re-run changes nothing. Both stop cleanly at the database soft limit and print where to resume.

```bash
cd apps/api
.venv/bin/python -m scripts.backfill_snapshot_translations --dry-run   # counts pages, writes nothing
.venv/bin/python -m scripts.backfill_translations                      # cards: queues missing or stale tasks
.venv/bin/python -m scripts.backfill_snapshot_translations             # pages: queues missing or stale tasks
```

- `backfill_snapshot_translations.py` has `--dry-run`. `backfill_translations.py` has no dry-run flag. To see what it
  queues, read `python -m discovery_ingest translate summary` (from `apps/discovery-ingest`) before and after the run.
- Both accept `--locale` to cover one target locale, `--batch-size` and `--after <id>` to resume after the id a previous run
  printed.
- Record the counts of each run in the run ledger.

## Snapshot schedule

The `snapshot-drain` job of `discovery-translate.yml` runs after the card drain, in the same `discovery-pipeline` group. It
claims at most five pages a claim, 60 claims, within 600 seconds. It skips without failing when the Actions minutes or
`azure_translator_chars` fall below the precheck, or when no page is ready.

- The job runs only when `SNAPSHOT_TRANSLATE_SCHEDULE` is `enabled`, including on manual dispatch.
- Before enabling it, run one drain by hand from a laptop, with `DISCOVERY_API_URL`, `DISCOVERY_API_KEY` and the Azure
  variables exported in the shell. Inspect the result on the coverage page, then set the variable:

  ```bash
  cd apps/discovery-ingest
  .venv/bin/python -m discovery_ingest translate drain --unit snapshot --max-tasks 5 --max-batches 1
  ```

- A page is skipped, not translated, when its cleaned text is under 200 characters (an empty shell) or when its language is
  not German. A page longer than 30,000 characters of cleaned text is cut and stored with `truncated` set.
- The stored translation is a list of typed text blocks: headings, paragraphs, list items, table rows and definition terms.
  The web app renders those blocks and never renders markup from the source.

## Rollback

1. Set the repository variable `TRANSLATION_ENGINE` so that `TRANSLATION_ENGINE=llm`. The card drain and `translate-ui`
   then use Workers AI again, on the neuron ledger, above the `QUERY_EMBED_RESERVE` floor. `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_AI_API_TOKEN` must
   be set as secrets. Setting the variable back to `azure-translator`, or deleting it, returns to Azure.
2. The snapshot job always uses `azure-translator`. To stop Azure spend on snapshots as well, set
   `SNAPSHOT_TRANSLATE_SCHEDULE` to any value other than `enabled`, or delete it.
3. Stop using Azure once the monthly cap is reached. The drains stop by themselves at the cap: the precheck skips the job,
   and a refused reservation stops the drain without consuming attempts. On F0, do not raise
   `BUDGET_AZURE_TRANSLATOR_CHARS_MONTHLY` to continue past the cap, because Azure stops the free tier at 2,000,000 and
   answers `403001`.

O4 is open until the first month of operation is seen. The ledger assumes that Azure's F0 allowance resets with the UTC
calendar month. If Azure resets on another day, a `403001` marks the current UTC month exhausted in the ledger and the
drains stop. A `403001` in the next month marks that month too, until Azure's own allowance resets. Record the outcome of
the first month in the run ledger.

## Data processing and region

The text sent to Azure is public procedure page text, and the candidate card titles and descriptions derived from it. Before
the probe, the operator records these three things in the run ledger:

- The endpoint. The default is the global host. A custom-domain endpoint pinned to an EU region is the operator's choice,
  set in `AZURE_TRANSLATOR_ENDPOINT`.
- The region of the Translator resource, set in `AZURE_TRANSLATOR_REGION`.
- The data-processing terms under which the pages are sent, and the date of the decision.

## First production steps (operator)

1. Confirm the O4 decision (the quota reset) and the O5 decision (data processing) are recorded.
2. On Render, set `TRANSLATION_TARGET_LOCALES` to `en tr ru uk pl ro` if it differs, and `BUDGET_AZURE_TRANSLATOR_CHARS_MONTHLY`
   only if a non-default cap is wanted.
3. Confirm the GitHub secrets and the `TRANSLATION_ENGINE` variable are present.
4. For each of `tr ru uk pl ro`, accept the strings by name and date in the manifest and run `enable_locale.py`. The script
   needs migration `20261112_locale_machine_flag` applied to the target database. See [locales.md](locales.md).
5. Run `backfill_translations.py` for cards, then `backfill_snapshot_translations.py`, as described in Backfill order.
6. Set `SNAPSHOT_TRANSLATE_SCHEDULE=enabled` after one inspected manual snapshot drain (see Snapshot schedule).
7. Check the coverage page (`/admin/discovery/coverage`, its Translator section and per-locale translation coverage) and the
   monthly meter for two runs, and record them in the run ledger.
