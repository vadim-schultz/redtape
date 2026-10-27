# discovery-ingest

CLI workers that upsert discovery catalogue rows via the RedTape machine API (`X-API-Key`).

## Environment

`DISCOVERY_API_URL` is the **API host root** — not the machine path. The client appends
`/api/v1/discovery/machine/...` (see [`api_client.py`](discovery_ingest/api_client.py)).

| Variable | Required | Example |
| --- | --- | --- |
| `DISCOVERY_API_URL` | yes | `http://localhost:8000` or `https://redtape-api.onrender.com` |
| `DISCOVERY_API_KEY` | yes | `rt_…` from `python -m scripts.issue_api_key` in `apps/api` |
| `GOVDATA_CKAN_BASE_URL` | no | Default in [`config.py`](discovery_ingest/config.py) |
| `PVOG_API_BASE_URL` | no | Default in `config.py` |
| `FIM_PORTAL_BASE_URL` | no | Default in `config.py` |
| `BOT_CONTACT_URL` | no | Contact URL in the `RedtapeBot/1.0 (+<url>)` User-Agent; defaults to the repository URL |
| `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_BROWSER_API_TOKEN` | only for browser kinds and `browser probe` | Cloudflare account and a custom token with only "Browser Run - Edit" |
| `BROWSER_MIN_INTERVAL_SECONDS`, `BROWSER_REQUEST_TIMEOUT_SECONDS` | no | Seconds between the end of one Cloudflare call and the start of the next (default 11) and the per-call timeout (default 60) |

Copy [`.env.example`](.env.example) to `.env` for local runs.

### Issue a machine API key

From `apps/api` (venv active, migrations applied):

```bash
python -m scripts.issue_api_key --name discovery-ingest-local
```

GitHub Actions scheduled discovery uses `discovery-scheduled-gha` — store the printed key in the
`DISCOVERY_API_KEY` repository secret. See [`docs/operations/scheduled-jobs.md`](../../docs/operations/scheduled-jobs.md).

## GovData OZG

```bash
export DISCOVERY_API_URL=http://localhost:8000
export DISCOVERY_API_KEY=rt_<your-key>
python -m discovery_ingest govdata run \
  --input path/to/ozg-export.json \
  --jurisdiction-id 11111111-1111-1111-1111-111111111101
```

Federal rows (`ars` `000000000000`) use `--jurisdiction-id` as the Germany country jurisdiction UUID.

Operations runbook: [`docs/operations/discovery-layer.md`](../../docs/operations/discovery-layer.md).

## Render pages through Cloudflare Browser Run

`render_page` (and later `capture_screenshot`) tasks spend Cloudflare browser time, so they are never in the default
kinds. The free plan allows 10 browser minutes a day and one request every 10 seconds; every run also shares one daily
budget ledger (`GET /machine/budgets`) with every other run.

```bash
# Check the quick actions and the credentials (prints a table, never the token; needs only the two Cloudflare variables):
python -m discovery_ingest browser probe --url https://example.com --variant content

# Drain the render queue; fails before claiming without the Cloudflare variables or artifact storage:
python -m discovery_ingest worker drain --kinds render_page --max-tasks 5 --max-batches 40 \
  --time-budget-seconds 900 --browser-budget-seconds 480
```

A browser limit (`browser_budget`, `browser_quota`), unavailable storage (`storage_unavailable`) or the database soft
limit (`db_limit`) releases the in-flight and unstarted tasks and ends the run successfully; only a rejected token or an
API failure fails it. The manual workflows are `discovery-browser-probe.yml` and `discovery-render.yml`.
