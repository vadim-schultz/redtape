#!/bin/bash
set -e  # Exit on any error

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

PYTHONPATH=. \
  DATABASE_URL="sqlite:///test.db" \
  uv run pytest

echo "=== Web Checks ==="
cd ../web

echo "Installing/updating frontend dependencies (if needed)..."
#
# In some environments, `npm ci` can be flaky due to DNS/network variability.
# Keep CI deterministic and fast by only running a fresh install if `eslint` isn't present.
if [ ! -x node_modules/.bin/eslint ] || [ ! -x node_modules/.bin/vitest ]; then
  npm install --foreground-scripts --no-audit --no-fund
else
  echo "eslint and vitest binaries present; skipping npm install"
fi

NODE_OPTIONS="--max-old-space-size=8192" npm run lint
NODE_OPTIONS="--max-old-space-size=8192" npm run format:check
NODE_OPTIONS="--max-old-space-size=8192" npm run typecheck
NODE_OPTIONS="--max-old-space-size=8192" npm test
NODE_OPTIONS="--max-old-space-size=8192" npm run build

echo "✅ All CI checks passed!"

