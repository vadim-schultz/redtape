# discovery-ingest

CLI workers that upsert discovery catalogue rows via the RedTape machine API (`X-API-Key`).

## GovData OZG

```bash
export DISCOVERY_API_URL=https://api.example
export DISCOVERY_API_KEY=...
python -m discovery_ingest govdata run \
  --input path/to/ozg-export.json \
  --jurisdiction-id 11111111-1111-1111-1111-111111111101
```

Federal rows (`ars` `000000000000`) use `--jurisdiction-id` as the Germany country jurisdiction UUID.
