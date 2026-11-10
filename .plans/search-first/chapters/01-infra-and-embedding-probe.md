---
name: "Chapter 1 — Infra and embedding probe"
overview: "Make pgvector available locally, in CI and in tests, add the search settings, and probe Workers AI to fix the embedding dimension and batch limit before any schema is written."
id: C1
depends_on: []
touches:
  - docker-compose.yml
  - .github/workflows/api-lint-test.yml
  - apps/api/pyproject.toml
  - apps/api/uv.lock
  - apps/api/app/config.py
  - apps/api/tests/conftest.py
  - apps/discovery-ingest/discovery_ingest/extract/embedding/
  - apps/discovery-ingest/discovery_ingest/cli/embed/
  - apps/discovery-ingest/tests/
  - docs/operations/local-development.md
  - .env.example
execution: chapter-implementer
todos:
  - id: pgvector-infra
    content: "Switch local and CI Postgres to a pgvector image, add the pgvector Python package, and create the extension in test setup."
    status: pending
  - id: settings
    content: "Add validated search and embedding settings to the API configuration."
    status: pending
  - id: embedding-client-probe
    content: "Add a minimal Workers AI embedding client and an embed probe command that reports dimension, batch limit, latency and neurons."
    status: pending
  - id: tests
    content: "Add settings validation, extension availability, probe parsing and probe error tests."
    status: pending
---

# Chapter 1 — Infra and embedding probe

**Repo:** `redtape` (`docker-compose.yml`, `.github`, `apps/api`, `apps/discovery-ingest`)
**Depends on:** none · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

## Goal

Remove the infrastructure unknowns before any schema work: the database must be able to hold vectors in every environment, and the embedding model's real output dimension and limits must be known. The probe result fixes `EMBEDDING_DIM`, which chapter 3 uses for `vector(N)`.

## Design decisions

- Replace `postgres:16-alpine` with `pgvector/pgvector:pg16` in `docker-compose.yml` and in both jobs of `.github/workflows/api-lint-test.yml`. Same major version, so data and tooling are unchanged.
- Add the `pgvector` Python package to `apps/api/pyproject.toml` (SQLAlchemy `Vector` type). Commit the resulting `uv.lock` change.
- `apps/api/tests/conftest.py` builds the schema with `Base.metadata.create_all`, not Alembic. Run `CREATE EXTENSION IF NOT EXISTS vector` (and `unaccent`) on the test engine before `create_all`, so models that use `Vector` and `unaccent` work in unit tests. Chapter 3's migration creates the same extensions for real databases.
- Settings in `apps/api/app/config.py`, in the existing `Field(default, description)` style, validated at load:
  - `EMBEDDING_MODEL` (default `@cf/qwen/qwen3-embedding-0.6b`), `EMBEDDING_DIM` (set from the probe);
  - `SEARCH_HYBRID_ENABLED` (default `false`), `RRF_K` (60), `SEARCH_TOP_N` (50), `SEARCH_FUSED_TOP_K` (100), `SEARCH_MIN_SIMILARITY` (0..1);
  - `QUERY_EMBED_TIMEOUT_S`, `QUERY_EMBED_CACHE_SIZE`;
  - `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_AI_API_TOKEN` (optional; empty means the query embedder is unavailable and search degrades to keyword).
- Embedding client in `discovery_ingest/extract/embedding/`: `CloudflareEmbeddingClient.embed(texts)` over the existing endpoint table (`extract/llm/endpoints.py`, add `ai/run/{model}` use for embeddings), reusing the `Throttle`, the error taxonomy in `extract/llm/classify.py` and `errors.py`, and secret scrubbing. Batching, metering and the drain are chapter 6.
- `python -m discovery_ingest embed probe` prints one JSON report (model, dimension, which reduced dimensions the `dimensions` (Matryoshka) parameter accepts, largest accepted batch, latency, token count, neurons) in the style of `llm probe`. It never prints the token.
- The gate is a recorded decision: the probe's dimension, the chosen column type (`vector` or `halfvec`) and any reduced dimension are written to [../run-ledger.md](../run-ledger.md) together with a projection of the total database size for seven locale rows per candidate (about 4000 candidates × 7 × bytes per row, plus the HNSW index, search text and tsvectors, added to the measured current size; the product owner reports about 83 MB of 500 MB used) checked against `DB_SOFT_LIMIT_BYTES` with margin (rollout invariant 11). Translation text is not part of the projection: it lives in R2 (D17). `EMBEDDING_DIM` is set from that decision.

## Files

| Path | Change |
| --- | --- |
| `docker-compose.yml` | `db` service image `pgvector/pgvector:pg16`. |
| `.github/workflows/api-lint-test.yml` | Both Postgres service images (`:31` and `:84`) to the pgvector image. |
| `apps/api/pyproject.toml`, `apps/api/uv.lock` | Add `pgvector`. |
| `apps/api/app/config.py` | New validated settings. |
| `apps/api/tests/conftest.py` | Create `vector` and `unaccent` extensions before `create_all`. |
| `apps/api/tests/test_config_search.py` | Settings defaults and validation. |
| `apps/api/tests/test_pgvector_available.py` | Extension present; a vector round trip works. |
| `apps/discovery-ingest/discovery_ingest/extract/embedding/client.py` | `CloudflareEmbeddingClient` and result model. |
| `apps/discovery-ingest/discovery_ingest/extract/embedding/probe.py` | Probe logic and report model. |
| `apps/discovery-ingest/discovery_ingest/cli/embed/` | `embed probe` command, registered in `cli/main.py`. |
| `apps/discovery-ingest/tests/test_embedding_client.py`, `test_embed_probe.py` | Client and probe tests with a fake HTTP transport. |
| `docs/operations/local-development.md`, `.env.example` | New image, new variables, the extension requirement. |

## Red tests

### Happy path

- `config · search settings load defaults and accept overrides` asserts documented defaults and that overrides parse.
- `pgvector · extension is available and a vector round trips` asserts `select extversion from pg_extension where extname = 'vector'` returns a row and a stored vector compares by cosine distance.
- `embedding client · parses a successful response` asserts one vector per input text, in order, with the dimension taken from the response.
- `embed probe · reports dimension, batch limit and neurons` asserts the report fields from a canned response sequence.

### Negative path

- `config · rejects an invalid dimension, k or similarity` asserts `EMBEDDING_DIM <= 0`, `RRF_K <= 0` and `SEARCH_MIN_SIMILARITY` outside 0..1 fail at load.
- `embedding client · maps 401 and 403 to an auth error, 429 to a quota error` asserts the existing taxonomy and that the token never appears in the error text.
- `embedding client · a response with a vector count that differs from the input count is an error` asserts no silent truncation.
- `embed probe · stops at the first rejected batch size and reports the last good one`.

Run the narrow suites first and confirm they fail for the intended reason.

## Green

1. Swap the images and add the dependency; make the extension tests pass.
2. Add settings and their validation.
3. Add the client and the probe; run the probe once with a real token (operator machine) and record the output.
4. Set the `EMBEDDING_DIM` default from the recorded dimension.

## Refactor gate

Audit the new modules and `config.py`:

- the settings block stays grouped and documented, no duplicated defaults;
- the client has no boolean parameters and no `Any`; response parsing is one small function;
- the probe report is a typed model, not a dict;
- error classification is reused from `extract/llm/classify.py`, not copied.

## Verification

```bash
docker compose up -d db
cd apps/api
uv run pytest tests/test_config_search.py tests/test_pgvector_available.py
uv run ruff format --check . && uv run ruff check . && uv run mypy app scripts
cd ../discovery-ingest
uv run pytest tests/test_embedding_client.py tests/test_embed_probe.py
cd ../.. && ./ci.sh
```

Record the probe report, the pgvector version of the local image, and (operator) the Supabase check from the rollout in [../run-ledger.md](../run-ledger.md).

## Out of scope

Any schema, batching, neuron metering, the drain, the query embedder, and the instruction prefix for queries.

## Git workflow

```bash
git checkout feat/plans-search-first && git pull
git checkout -b feat/search-infra-and-probe
```

```text
test(api): describe search settings and pgvector availability
feat(infra): run pgvector in local and CI Postgres
feat(ingest): add Workers AI embedding client and probe
```
