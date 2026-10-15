# Discovery fixture index

JSON and HTTP fixtures for government API clients live in **`apps/discovery-ingest/tests/fixtures/`** once
chapters 12–13–17 land. This directory only documents intended paths.

| Path | Chapter | Source |
| --- | --- | --- |
| `apps/discovery-ingest/tests/fixtures/govdata/*.json` | 12 | GovData OZG **Leistungen** JSON shape (`open-pvog` page) |
| `apps/discovery-ingest/tests/fixtures/pvog/*.json` | 13 | PVOG Suchdienst paginated responses (`nextPageToken` / list pages) |
| `apps/discovery-ingest/tests/fixtures/fim/*.json` | 17 | FIM steckbrief / stammtext snippets |
| `apps/discovery-ingest/tests/fixtures/leika/*.json` | 17 | Same host as FIM; `source=leika` payloads |

Canon URLs and `raw_payload` keys: [government-data-sources.md](../government-data-sources.md).
