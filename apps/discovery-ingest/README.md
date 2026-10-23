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
