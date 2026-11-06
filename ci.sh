#!/bin/bash
set -e  # Exit on any error

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# True when both the Docker CLI and the compose plugin are usable.
have_docker_compose() {
  command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1
}

# Drop and recreate a database on the compose `db` service, so the step that
# uses it starts from an empty schema.
recreate_ci_database() {
  local name="$1"
  if have_docker_compose; then
    (cd "$ROOT" && docker compose exec -T db psql -U postgres \
      -c "DROP DATABASE IF EXISTS ${name};" \
      -c "CREATE DATABASE ${name};")
  else
    echo "Docker not found; skipping ${name} database (re)creation, the step that uses it may fail." >&2
  fi
}

echo "=== API Checks ==="
cd apps/api

# Match GitHub workflow commands from `.github/workflows/api-lint-test.yml`.
# Uses `uv` to install the API + dev dependencies for deterministic tooling.
# Note: locally we avoid `--system` because Python may be "externally managed".
if [ ! -d ".venv" ] || [ ! -x ".venv/bin/ruff" ]; then
  uv pip install -e ".[dev]"
else
  echo "API venv present ('.venv/bin/ruff'); skipping uv install"
fi

PYTHONPATH=. \
  DATABASE_URL="sqlite:///test.db" \
  uv run ruff format --check .

PYTHONPATH=. \
  DATABASE_URL="sqlite:///test.db" \
  uv run ruff check .

PYTHONPATH=. \
  DATABASE_URL="sqlite:///test.db" \
  uv run mypy app scripts

# DB-backed tests need Postgres (app/config.py defaults DATABASE_URL to the
# compose db); start it if nothing is listening on 5432 yet. Without Docker,
# tests fall back to skipping — export REQUIRE_DB=0 to silence the reason.
if ! (exec 3<>/dev/tcp/127.0.0.1/5432) 2>/dev/null; then
  if have_docker_compose; then
    echo "Postgres not reachable on 5432; starting 'docker compose up -d --wait db'..."
    (cd "$ROOT" && docker compose up -d --wait db)
  else
    echo "Docker not found; DB-backed tests will fail (set REQUIRE_DB=0 to skip them instead)." >&2
  fi
fi

# Migration round trip: single head, upgrade, downgrade+upgrade, drift check.
# Own database, dropped and recreated so it starts truly empty — separate
# from the pytest database, so a stray `create_all` can't hide a missing
# migration.
MIGRATIONS_DB="redtape_migrations"
recreate_ci_database "${MIGRATIONS_DB}"

PYTHONPATH=. \
  DATABASE_URL="postgresql+psycopg://postgres:postgres@127.0.0.1:5432/${MIGRATIONS_DB}" \
  uv run bash scripts/check_migrations.sh

# Pytest database: own database, dropped and recreated so every run starts
# empty. Tests never touch the developer's `redtape` database.
PYTEST_DB="redtape_pytest"
recreate_ci_database "${PYTEST_DB}"

PYTHONPATH=. \
  DATABASE_URL="postgresql+psycopg://postgres:postgres@127.0.0.1:5432/${PYTEST_DB}" \
  REQUIRE_DB="${REQUIRE_DB:-1}" \
  uv run pytest

echo "=== Web Checks ==="
cd ../web

echo "Installing/updating frontend dependencies (if needed)..."
#
# In some environments, `npm ci` can be flaky due to DNS/network variability.
# Keep CI deterministic and fast by only running a fresh install if `eslint` isn't present.
if [ ! -x node_modules/.bin/eslint ] || [ ! -x node_modules/.bin/vitest ]; then
  "$ROOT/scripts/npm.sh" install --foreground-scripts --no-audit --no-fund
else
  echo "eslint and vitest binaries present; skipping npm install"
fi

if grep '"resolved":' package-lock.json | grep -v 'https://registry.npmjs.org/' | grep -q .; then
  echo "error: package-lock.json resolved URLs must use https://registry.npmjs.org" >&2
  exit 1
fi

NODE_OPTIONS="--max-old-space-size=8192" npm run lint
NODE_OPTIONS="--max-old-space-size=8192" npm run format:check
NODE_OPTIONS="--max-old-space-size=8192" npm run typecheck
NODE_OPTIONS="--max-old-space-size=8192" npm test
NODE_OPTIONS="--max-old-space-size=8192" npm run build

echo "=== Discovery skill checks ==="
bash "$ROOT/scripts/check_discovery_skills.sh" all

echo "=== Discovery ingest checks ==="
cd "$ROOT/apps/discovery-ingest"
if [ ! -d ".venv" ]; then
  uv venv
fi
if [ ! -x ".venv/bin/ruff" ]; then
  uv pip install -e ".[dev]"
else
  echo "discovery-ingest venv present; skipping uv install"
fi
uv run ruff format --check .
uv run ruff check .
uv run mypy discovery_ingest
uv run pytest

echo "✅ All CI checks passed!"

